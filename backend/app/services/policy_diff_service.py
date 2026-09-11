import re
import difflib
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.vendor import Vendor
from app.models.document import Document, PolicyVersion
from app.models.policy_diff import PolicyDiff
from app.schemas.policy_diff import (
    DiffLineType,
    WordDiffSchema,
    DiffLineSchema,
    SideBySideRowSchema,
    DiffHunkSchema,
    DiffStatsSchema,
    DeterministicDiffSchema,
    SemanticImpactSchema,
    MaterialityTier,
    RiskPostureImpact,
    RiskPillar,
    ClauseChangeItem,
    PolicyVersionSummary,
    PolicyDiffResponse,
)
from app.services.llm import BaseLLMService, get_llm_service

logger = logging.getLogger("vendorguard.services.policy_diff")



MAX_POLICY_LINES = 5000
MAX_SIDE_BY_SIDE_ROWS = 3000


def _tokenize_words(text: str) -> List[str]:
    """Splits text into words and punctuation/whitespace tokens for fine-grained diffing."""
    if not text:
        return []
    return re.findall(r"\w+|\s+|[^\w\s]", text)


def compute_word_diffs(old_line: str, new_line: str) -> Tuple[List[WordDiffSchema], List[WordDiffSchema]]:
    """
    Computes token/word-level diffs between an old line and a new line.
    Returns (left_words, right_words).
    """
    old_tokens = _tokenize_words(old_line)
    new_tokens = _tokenize_words(new_line)

    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens)
    left_words: List[WordDiffSchema] = []
    right_words: List[WordDiffSchema] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            eq_text_left = "".join(old_tokens[i1:i2])
            eq_text_right = "".join(new_tokens[j1:j2])
            left_words.append(WordDiffSchema(type="unchanged", text=eq_text_left))
            right_words.append(WordDiffSchema(type="unchanged", text=eq_text_right))
        elif tag == "replace":
            del_text = "".join(old_tokens[i1:i2])
            add_text = "".join(new_tokens[j1:j2])
            left_words.append(WordDiffSchema(type="deleted", text=del_text))
            right_words.append(WordDiffSchema(type="added", text=add_text))
        elif tag == "delete":
            del_text = "".join(old_tokens[i1:i2])
            left_words.append(WordDiffSchema(type="deleted", text=del_text))
        elif tag == "insert":
            add_text = "".join(new_tokens[j1:j2])
            right_words.append(WordDiffSchema(type="added", text=add_text))

    return left_words, right_words


def compute_deterministic_diff(
    old_text: Optional[str],
    new_text: Optional[str],
    context_lines: int = 3,
    max_lines: int = MAX_POLICY_LINES,
) -> DeterministicDiffSchema:
    """
    Computes deterministic line-by-line, word-level, unified, and side-by-side diffs.
    Handles empty content, identical content, and protects against large documents.
    """
    old_raw = old_text or ""
    new_raw = new_text or ""

    old_lines = old_raw.splitlines()
    new_lines = new_raw.splitlines()

    total_lines_old = len(old_lines)
    total_lines_new = len(new_lines)

    is_truncated = False
    truncation_note = None

    if total_lines_old > max_lines or total_lines_new > max_lines:
        is_truncated = True
        truncation_note = (
            f"Content truncated to first {max_lines} lines for diff performance "
            f"(Original: old={total_lines_old}, new={total_lines_new} lines)."
        )
        old_lines = old_lines[:max_lines]
        new_lines = new_lines[:max_lines]

    # Identical check
    if old_raw == new_raw:
        stats = DiffStatsSchema(
            total_lines_old=total_lines_old,
            total_lines_new=total_lines_new,
            added_lines=0,
            deleted_lines=0,
            changed_lines=0,
            is_identical=True,
            is_truncated=is_truncated,
            truncation_note=truncation_note,
        )

        # Build collapsed or single context side-by-side view for identical content
        sbs_rows: List[SideBySideRowSchema] = []
        sample_limit = min(len(old_lines), 50)
        for idx in range(sample_limit):
            sbs_rows.append(
                SideBySideRowSchema(
                    row_type="unchanged",
                    left_line_no=idx + 1,
                    left_content=old_lines[idx],
                    left_type="unchanged",
                    right_line_no=idx + 1,
                    right_content=new_lines[idx],
                    right_type="unchanged",
                )
            )

        return DeterministicDiffSchema(
            stats=stats,
            unified_hunks=[],
            side_by_side_rows=sbs_rows,
            raw_unified_diff="",
        )

    # Compute raw unified diff using difflib
    unified_diff_generator = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="old_version",
        tofile="new_version",
        lineterm="",
        n=context_lines,
    )
    raw_diff_lines = list(unified_diff_generator)
    raw_unified_diff = "\n".join(raw_diff_lines)

    # Parse unified diff into structured hunks
    unified_hunks: List[DiffHunkSchema] = []
    current_hunk: Optional[DiffHunkSchema] = None
    curr_old_no = 0
    curr_new_no = 0
    added_count = 0
    deleted_count = 0

    hunk_header_regex = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)$")

    for line in raw_diff_lines:
        if line.startswith("---") or line.startswith("+++"):
            continue

        match = hunk_header_regex.match(line)
        if match:
            if current_hunk:
                unified_hunks.append(current_hunk)

            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) is not None else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) is not None else 1

            curr_old_no = old_start
            curr_new_no = new_start

            current_hunk = DiffHunkSchema(
                old_start=old_start,
                old_lines_count=old_count,
                new_start=new_start,
                new_lines_count=new_count,
                header=line,
                lines=[],
            )
            continue

        if current_hunk is None:
            continue

        if line.startswith("+"):
            added_count += 1
            content = line[1:]
            current_hunk.lines.append(
                DiffLineSchema(
                    type=DiffLineType.ADDED,
                    old_line_no=None,
                    new_line_no=curr_new_no,
                    content=content,
                )
            )
            curr_new_no += 1
        elif line.startswith("-"):
            deleted_count += 1
            content = line[1:]
            current_hunk.lines.append(
                DiffLineSchema(
                    type=DiffLineType.DELETED,
                    old_line_no=curr_old_no,
                    new_line_no=None,
                    content=content,
                )
            )
            curr_old_no += 1
        elif line.startswith(" "):
            content = line[1:]
            current_hunk.lines.append(
                DiffLineSchema(
                    type=DiffLineType.UNCHANGED,
                    old_line_no=curr_old_no,
                    new_line_no=curr_new_no,
                    content=content,
                )
            )
            curr_old_no += 1
            curr_new_no += 1

    if current_hunk:
        unified_hunks.append(current_hunk)

    # Compute side-by-side rows using SequenceMatcher
    side_by_side_rows: List[SideBySideRowSchema] = []
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if len(side_by_side_rows) >= MAX_SIDE_BY_SIDE_ROWS:
            is_truncated = True
            truncation_note = (
                truncation_note or f"Side-by-side view capped at {MAX_SIDE_BY_SIDE_ROWS} rows for performance."
            )
            break

        if tag == "equal":
            for idx in range(i2 - i1):
                if len(side_by_side_rows) >= MAX_SIDE_BY_SIDE_ROWS:
                    break
                old_idx = i1 + idx
                new_idx = j1 + idx
                side_by_side_rows.append(
                    SideBySideRowSchema(
                        row_type="unchanged",
                        left_line_no=old_idx + 1,
                        left_content=old_lines[old_idx],
                        left_type="unchanged",
                        right_line_no=new_idx + 1,
                        right_content=new_lines[new_idx],
                        right_type="unchanged",
                    )
                )

        elif tag == "delete":
            for idx in range(i1, i2):
                if len(side_by_side_rows) >= MAX_SIDE_BY_SIDE_ROWS:
                    break
                side_by_side_rows.append(
                    SideBySideRowSchema(
                        row_type="deleted",
                        left_line_no=idx + 1,
                        left_content=old_lines[idx],
                        left_type="deleted",
                        right_line_no=None,
                        right_content=None,
                        right_type=None,
                    )
                )

        elif tag == "insert":
            for idx in range(j1, j2):
                if len(side_by_side_rows) >= MAX_SIDE_BY_SIDE_ROWS:
                    break
                side_by_side_rows.append(
                    SideBySideRowSchema(
                        row_type="added",
                        left_line_no=None,
                        left_content=None,
                        left_type=None,
                        right_line_no=idx + 1,
                        right_content=new_lines[idx],
                        right_type="added",
                    )
                )

        elif tag == "replace":
            old_chunk = old_lines[i1:i2]
            new_chunk = new_lines[j1:j2]
            max_chunk_len = max(len(old_chunk), len(new_chunk))

            for idx in range(max_chunk_len):
                if len(side_by_side_rows) >= MAX_SIDE_BY_SIDE_ROWS:
                    break

                has_old = idx < len(old_chunk)
                has_new = idx < len(new_chunk)

                old_line = old_chunk[idx] if has_old else None
                new_line = new_chunk[idx] if has_new else None

                left_words: Optional[List[WordDiffSchema]] = None
                right_words: Optional[List[WordDiffSchema]] = None

                if has_old and has_new and old_line is not None and new_line is not None:
                    left_words, right_words = compute_word_diffs(old_line, new_line)

                side_by_side_rows.append(
                    SideBySideRowSchema(
                        row_type="modified",
                        left_line_no=(i1 + idx + 1) if has_old else None,
                        left_content=old_line,
                        left_type="deleted" if has_old else None,
                        right_line_no=(j1 + idx + 1) if has_new else None,
                        right_content=new_line,
                        right_type="added" if has_new else None,
                        left_words=left_words,
                        right_words=right_words,
                    )
                )

    stats = DiffStatsSchema(
        total_lines_old=total_lines_old,
        total_lines_new=total_lines_new,
        added_lines=added_count,
        deleted_lines=deleted_count,
        changed_lines=added_count + deleted_count,
        is_identical=False,
        is_truncated=is_truncated,
        truncation_note=truncation_note,
    )

    return DeterministicDiffSchema(
        stats=stats,
        unified_hunks=unified_hunks,
        side_by_side_rows=side_by_side_rows,
        raw_unified_diff=raw_unified_diff,
    )


async def analyze_policy_diff_semantic(
    vendor_name: str,
    document_type: str,
    deterministic_diff: DeterministicDiffSchema,
    llm_service: Optional[BaseLLMService] = None,
) -> SemanticImpactSchema:
    """
    Executes AI semantic change impact analysis on policy diff.
    - If diff is identical (0 changes): returns deterministic neutral response.
    - If diff has changes: invokes LLM (Ollama -> OpenAI) with diff context.
    - If LLM fails: returns robust graceful fallback synthesized from deterministic diff stats.
    """
    stats = deterministic_diff.stats

    # 1. Identical version short-circuit
    if stats.is_identical or stats.changed_lines == 0:
        return SemanticImpactSchema(
            executive_change_summary=f"No contractual, privacy, or security changes detected between these versions of {document_type}.",
            materiality=MaterialityTier.LOW,
            affected_clauses=[],
            clause_category="Administrative / Identical",
            modification_intent="Identical document content preserved across both versions.",
            affected_risk_pillar=RiskPillar.MULTIPLE,
            risk_posture=RiskPostureImpact.NEUTRAL,
            risk_delta_explanation="Both versions are bitwise identical in content. No risk drift occurred.",
            clause_breakdown=[],
        )

    # 2. Extract compact diff context for LLM prompt
    diff_snippets: List[str] = []
    max_context_chars = 6000
    current_chars = 0

    for hunk in deterministic_diff.unified_hunks:
        if current_chars >= max_context_chars:
            diff_snippets.append("... [additional diff hunks truncated for brevity] ...")
            break
        hunk_str = f"{hunk.header}\n" + "\n".join(
            f"{'+' if l.type == DiffLineType.ADDED else ('-' if l.type == DiffLineType.DELETED else ' ')}{l.content}"
            for l in hunk.lines
        )
        diff_snippets.append(hunk_str)
        current_chars += len(hunk_str)

    diff_context = "\n".join(diff_snippets) if diff_snippets else deterministic_diff.raw_unified_diff[:max_context_chars]

    # 3. Invoke LLM service with fallback
    service = llm_service or get_llm_service()
    try:
        impact = await service.analyze_policy_diff(
            vendor_name=vendor_name,
            document_type=document_type,
            diff_context=diff_context,
        )
        return impact

    except Exception as exc:
        logger.warning(
            "Semantic analysis LLM invocation failed (%s). Applying deterministic fallback synthesis.",
            str(exc),
        )

        # Determine fallback materiality based on volume of changes
        if stats.changed_lines > 50:
            materiality = MaterialityTier.HIGH
        elif stats.changed_lines > 15:
            materiality = MaterialityTier.MEDIUM
        else:
            materiality = MaterialityTier.LOW

        summary = (
            f"Policy diff analysis detected {stats.added_lines} line(s) added and "
            f"{stats.deleted_lines} line(s) removed in {vendor_name}'s {document_type}."
        )

        return SemanticImpactSchema(
            executive_change_summary=summary,
            materiality=materiality,
            affected_clauses=["Policy Document Clauses"],
            clause_category="Contractual Terms Update",
            modification_intent="Vendor published revisions to policy terms during monitoring period.",
            affected_risk_pillar=RiskPillar.MULTIPLE,
            risk_posture=RiskPostureImpact.NEUTRAL,
            risk_delta_explanation=(
                f"Document content modified (+{stats.added_lines}/-{stats.deleted_lines} lines). "
                f"Automated deterministic fallback applied."
            ),
            clause_breakdown=[],
        )


async def get_document_versions(
    db: AsyncSession,
    vendor_id: str,
    document_id: str
) -> List[PolicyVersionSummary]:
    """Retrieves all historical policy versions for a specific document belonging to vendor."""
    v_id = str(vendor_id).strip()
    d_id = str(document_id).strip()

    # 1. Verify vendor exists
    v_stmt = select(Vendor).where(Vendor.id == v_id)
    v_res = await db.execute(v_stmt)
    vendor = v_res.scalar_one_or_none()
    if not vendor:
        raise ValueError(f"Vendor with ID '{v_id}' not found.")

    # 2. Verify document exists and belongs to vendor
    d_stmt = select(Document).where(Document.id == d_id)
    d_res = await db.execute(d_stmt)
    doc = d_res.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document with ID '{d_id}' not found.")
    if doc.vendor_id != v_id:
        raise ValueError(f"Document with ID '{d_id}' does not belong to vendor '{v_id}'.")

    # 3. Retrieve versions ordered by version_number descending
    pv_stmt = (
        select(PolicyVersion)
        .where(PolicyVersion.document_id == d_id)
        .order_by(PolicyVersion.version_number.desc())
    )
    pv_res = await db.execute(pv_stmt)
    versions = pv_res.scalars().all()

    summaries: List[PolicyVersionSummary] = []
    for pv in versions:
        lines = pv.raw_content.splitlines() if pv.raw_content else []
        summaries.append(
            PolicyVersionSummary(
                id=pv.id,
                document_id=pv.document_id,
                version_number=pv.version_number,
                content_hash=pv.content_hash,
                crawled_at=pv.crawled_at,
                summary=pv.summary,
                change_summary=pv.change_summary,
                line_count=len(lines),
            )
        )

    return summaries


async def get_or_compute_policy_diff(
    db: AsyncSession,
    vendor_id: str,
    document_id: str,
    old_version_id: str,
    new_version_id: str,
    llm_service: Optional[BaseLLMService] = None,
) -> PolicyDiffResponse:
    """
    Retrieves or computes structured policy diff and AI semantic impact analysis.
    Uses cached PolicyDiff from database if previously analyzed.
    Validates ownership, relationships, and version validity.
    """
    v_id = str(vendor_id).strip()
    d_id = str(document_id).strip()
    v1_id = str(old_version_id).strip()
    v2_id = str(new_version_id).strip()

    # 1. Verify Vendor
    v_stmt = select(Vendor).where(Vendor.id == v_id)
    v_res = await db.execute(v_stmt)
    vendor = v_res.scalar_one_or_none()
    if not vendor:
        raise ValueError(f"Vendor with ID '{v_id}' not found.")

    # 2. Verify Document
    d_stmt = select(Document).where(Document.id == d_id)
    d_res = await db.execute(d_stmt)
    doc = d_res.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document with ID '{d_id}' not found.")
    if doc.vendor_id != v_id:
        raise ValueError(f"Document with ID '{d_id}' does not belong to vendor '{v_id}'.")

    # 3. Verify Version 1
    pv1_stmt = select(PolicyVersion).where(PolicyVersion.id == v1_id)
    pv1_res = await db.execute(pv1_stmt)
    old_ver = pv1_res.scalar_one_or_none()
    if not old_ver:
        raise ValueError(f"Policy version '{v1_id}' not found.")
    if old_ver.document_id != d_id:
        raise ValueError(f"Version '{v1_id}' does not belong to document '{d_id}'.")

    # 4. Verify Version 2
    pv2_stmt = select(PolicyVersion).where(PolicyVersion.id == v2_id)
    pv2_res = await db.execute(pv2_stmt)
    new_ver = pv2_res.scalar_one_or_none()
    if not new_ver:
        raise ValueError(f"Policy version '{v2_id}' not found.")
    if new_ver.document_id != d_id:
        raise ValueError(f"Version '{v2_id}' does not belong to document '{d_id}'.")

    old_lines = old_ver.raw_content.splitlines() if old_ver.raw_content else []
    new_lines = new_ver.raw_content.splitlines() if new_ver.raw_content else []

    old_ver_summary = PolicyVersionSummary(
        id=old_ver.id,
        document_id=old_ver.document_id,
        version_number=old_ver.version_number,
        content_hash=old_ver.content_hash,
        crawled_at=old_ver.crawled_at,
        summary=old_ver.summary,
        change_summary=old_ver.change_summary,
        line_count=len(old_lines),
    )

    new_ver_summary = PolicyVersionSummary(
        id=new_ver.id,
        document_id=new_ver.document_id,
        version_number=new_ver.version_number,
        content_hash=new_ver.content_hash,
        crawled_at=new_ver.crawled_at,
        summary=new_ver.summary,
        change_summary=new_ver.change_summary,
        line_count=len(new_lines),
    )

    # Compute deterministic diff
    deterministic_diff = compute_deterministic_diff(old_ver.raw_content, new_ver.raw_content)

    # Identical versions case
    if v1_id == v2_id or deterministic_diff.stats.is_identical:
        semantic_impact = await analyze_policy_diff_semantic(
            vendor_name=vendor.name,
            document_type=doc.document_type,
            deterministic_diff=deterministic_diff,
            llm_service=llm_service,
        )
        return PolicyDiffResponse(
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            document_id=doc.id,
            document_title=doc.title,
            document_type=doc.document_type,
            old_version=old_ver_summary,
            new_version=new_ver_summary,
            deterministic_diff=deterministic_diff,
            semantic_impact=semantic_impact,
            is_cached=False,
            analyzed_at=datetime.now(timezone.utc),
        )

    # Check cache for existing PolicyDiff
    cached_stmt = select(PolicyDiff).where(
        PolicyDiff.old_version_id == v1_id,
        PolicyDiff.new_version_id == v2_id,
    )
    cached_res = await db.execute(cached_stmt)
    cached_diff = cached_res.scalar_one_or_none()

    if cached_diff:
        # Reconstruct SemanticImpactSchema from cached model
        clause_breakdown_raw = cached_diff.clause_breakdown or []
        clause_breakdown = [
            ClauseChangeItem(**item) if isinstance(item, dict) else item
            for item in clause_breakdown_raw
        ]

        cached_impact = SemanticImpactSchema(
            executive_change_summary=cached_diff.executive_change_summary,
            materiality=MaterialityTier(cached_diff.materiality),
            affected_clauses=cached_diff.affected_clauses or [],
            clause_category=cached_diff.clause_category,
            modification_intent=cached_diff.modification_intent or "",
            affected_risk_pillar=RiskPillar(cached_diff.affected_risk_pillar),
            risk_posture=RiskPostureImpact(cached_diff.risk_posture),
            risk_delta_explanation=cached_diff.risk_delta_explanation or "",
            clause_breakdown=clause_breakdown,
        )

        return PolicyDiffResponse(
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            document_id=doc.id,
            document_title=doc.title,
            document_type=doc.document_type,
            old_version=old_ver_summary,
            new_version=new_ver_summary,
            deterministic_diff=deterministic_diff,
            semantic_impact=cached_impact,
            is_cached=True,
            analyzed_at=cached_diff.analyzed_at,
        )

    # Compute new semantic impact
    semantic_impact = await analyze_policy_diff_semantic(
        vendor_name=vendor.name,
        document_type=doc.document_type,
        deterministic_diff=deterministic_diff,
        llm_service=llm_service,
    )

    # Save to database cache
    analyzed_now = datetime.now(timezone.utc)
    clause_breakdown_dicts = [
        item.model_dump() if hasattr(item, "model_dump") else item
        for item in semantic_impact.clause_breakdown
    ]

    new_cached_record = PolicyDiff(
        document_id=doc.id,
        old_version_id=v1_id,
        new_version_id=v2_id,
        executive_change_summary=semantic_impact.executive_change_summary,
        materiality=semantic_impact.materiality.value,
        affected_clauses=semantic_impact.affected_clauses,
        clause_category=semantic_impact.clause_category,
        modification_intent=semantic_impact.modification_intent,
        affected_risk_pillar=semantic_impact.affected_risk_pillar.value,
        risk_posture=semantic_impact.risk_posture.value,
        risk_delta_explanation=semantic_impact.risk_delta_explanation,
        clause_breakdown=clause_breakdown_dicts,
        analyzed_at=analyzed_now,
    )

    db.add(new_cached_record)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.warning("Could not persist cached PolicyDiff record: %s", str(exc))

    return PolicyDiffResponse(
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        document_id=doc.id,
        document_title=doc.title,
        document_type=doc.document_type,
        old_version=old_ver_summary,
        new_version=new_ver_summary,
        deterministic_diff=deterministic_diff,
        semantic_impact=semantic_impact,
        is_cached=False,
        analyzed_at=analyzed_now,
    )


