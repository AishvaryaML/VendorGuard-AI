import pytest
from app.services.policy_diff_service import (
    compute_deterministic_diff,
    compute_word_diffs,
)


def test_compute_word_diffs():
    old_line = "We retain personal data for 30 days."
    new_line = "We retain personal data for 90 days."
    left_words, right_words = compute_word_diffs(old_line, new_line)

    assert any(w.type == "deleted" and "30" in w.text for w in left_words)
    assert any(w.type == "added" and "90" in w.text for w in right_words)


def test_diff_identical_text():
    text = "Section 1: Data Collection\nWe collect email and IP address.\nSection 2: Security\nData is encrypted."
    result = compute_deterministic_diff(text, text)

    assert result.stats.is_identical is True
    assert result.stats.added_lines == 0
    assert result.stats.deleted_lines == 0
    assert result.stats.changed_lines == 0
    assert result.unified_hunks == []
    assert len(result.side_by_side_rows) > 0
    assert all(row.row_type == "unchanged" for row in result.side_by_side_rows)


def test_diff_empty_inputs():
    # Both empty
    res_both_empty = compute_deterministic_diff("", "")
    assert res_both_empty.stats.is_identical is True
    assert res_both_empty.stats.total_lines_old == 0
    assert res_both_empty.stats.total_lines_new == 0

    # Old empty, new has content (all additions)
    new_text = "Line 1: Hello\nLine 2: World"
    res_add = compute_deterministic_diff("", new_text)
    assert res_add.stats.is_identical is False
    assert res_add.stats.added_lines == 2
    assert res_add.stats.deleted_lines == 0

    # Old has content, new empty (all deletions)
    res_del = compute_deterministic_diff(new_text, "")
    assert res_del.stats.is_identical is False
    assert res_del.stats.deleted_lines == 2
    assert res_del.stats.added_lines == 0


def test_diff_mixed_modifications():
    old_text = (
        "1. Definitions\n"
        "2. Privacy: We do not share data with third parties.\n"
        "3. Security: We use AES-128 encryption.\n"
        "4. Contact: info@vendor.com\n"
    )
    new_text = (
        "1. Definitions\n"
        "2. Privacy: We share data with verified advertising partners.\n"
        "3. Security: We use AES-256 encryption.\n"
        "3.1 Sub-processors: We use cloud hosting.\n"
        "4. Contact: info@vendor.com\n"
    )

    result = compute_deterministic_diff(old_text, new_text)
    assert result.stats.is_identical is False
    assert result.stats.added_lines > 0
    assert result.stats.deleted_lines > 0
    assert len(result.unified_hunks) > 0

    # Check that modified lines have word diffs in side-by-side
    mod_rows = [r for r in result.side_by_side_rows if r.row_type == "modified"]
    assert len(mod_rows) > 0
    assert mod_rows[0].left_words is not None
    assert mod_rows[0].right_words is not None


def test_diff_large_document_protection():
    # Create document exceeding max lines
    large_old = "\n".join([f"Line {i}: Standard policy clause text." for i in range(100)])
    large_new = "\n".join([f"Line {i}: Modified policy clause text." for i in range(100)])

    # Test with custom small max_lines threshold
    result = compute_deterministic_diff(large_old, large_new, max_lines=20)
    assert result.stats.is_truncated is True
    assert "truncated" in result.stats.truncation_note.lower()
    assert result.stats.total_lines_old == 100
    assert result.stats.total_lines_new == 100
