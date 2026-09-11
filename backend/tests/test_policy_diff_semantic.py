import pytest
from unittest.mock import AsyncMock

from app.schemas.policy_diff import (
    SemanticImpactSchema,
    MaterialityTier,
    RiskPostureImpact,
    RiskPillar,
    ClauseChangeItem,
)
from app.services.policy_diff_service import (
    compute_deterministic_diff,
    analyze_policy_diff_semantic,
)
from app.services.llm import BaseLLMService


@pytest.mark.asyncio
async def test_semantic_analysis_identical_short_circuit():
    text = "Terms of service line 1\nLine 2"
    diff = compute_deterministic_diff(text, text)

    result = await analyze_policy_diff_semantic(
        vendor_name="Acme Corp",
        document_type="Terms of Service",
        deterministic_diff=diff,
    )

    assert result.materiality == MaterialityTier.LOW
    assert result.risk_posture == RiskPostureImpact.NEUTRAL
    assert "no contractual" in result.executive_change_summary.lower()
    assert result.affected_clauses == []


@pytest.mark.asyncio
async def test_semantic_analysis_with_mock_llm():
    old_text = "We retain data for 30 days."
    new_text = "We retain data for 10 years and may train AI models."
    diff = compute_deterministic_diff(old_text, new_text)

    mock_llm = AsyncMock(spec=BaseLLMService)
    mock_impact = SemanticImpactSchema(
        executive_change_summary="Vendor extended retention and introduced AI training rights.",
        materiality=MaterialityTier.HIGH,
        affected_clauses=["Data Retention", "AI Model Training"],
        clause_category="Data Privacy & Usage",
        modification_intent="Expand data monetization rights",
        affected_risk_pillar=RiskPillar.PRIVACY,
        risk_posture=RiskPostureImpact.ADVERSE,
        risk_delta_explanation="Retention extended significantly without user opt-out.",
        clause_breakdown=[
            ClauseChangeItem(
                clause_title="AI Training",
                change_type="Added",
                intent="Train models on customer data",
                impact_level="High",
                risk_pillar="Privacy",
                quote="train AI models",
            )
        ],
    )
    mock_llm.analyze_policy_diff.return_value = mock_impact

    result = await analyze_policy_diff_semantic(
        vendor_name="Acme Corp",
        document_type="Privacy Policy",
        deterministic_diff=diff,
        llm_service=mock_llm,
    )

    assert result.materiality == MaterialityTier.HIGH
    assert result.risk_posture == RiskPostureImpact.ADVERSE
    assert result.affected_risk_pillar == RiskPillar.PRIVACY
    assert "Retention extended" in result.risk_delta_explanation
    mock_llm.analyze_policy_diff.assert_called_once()


@pytest.mark.asyncio
async def test_semantic_analysis_llm_failure_fallback():
    old_text = "Line 1: Old text\nLine 2: Unchanged"
    new_text = "Line 1: New modified text\nLine 2: Unchanged\nLine 3: Extra clause"
    diff = compute_deterministic_diff(old_text, new_text)

    mock_llm = AsyncMock(spec=BaseLLMService)
    mock_llm.analyze_policy_diff.side_effect = RuntimeError("Ollama connection timeout")

    result = await analyze_policy_diff_semantic(
        vendor_name="Acme Corp",
        document_type="Privacy Policy",
        deterministic_diff=diff,
        llm_service=mock_llm,
    )

    # Must fall back gracefully without raising exception
    assert result.materiality in [MaterialityTier.LOW, MaterialityTier.MEDIUM, MaterialityTier.HIGH]
    assert "Acme Corp" in result.executive_change_summary
    assert "fallback applied" in result.risk_delta_explanation.lower()
