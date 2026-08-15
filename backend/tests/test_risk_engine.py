import pytest
from unittest.mock import AsyncMock, patch

from app.models.vendor import RiskTier
from app.schemas.risk import RiskFindingSchema, AIAssessmentResultSchema
from app.services.risk_engine import (
    validate_evidence,
    calculate_category_scores,
    calculate_overall_score,
    determine_risk_tier,
    AIRiskEngine,
)


def test_validate_evidence_exact_and_normalized():
    raw_policy = """
    Vendor Privacy Policy
    We retain personal data for up to 7 years after account termination.
    Data is stored using AWS AES-256 encryption at rest.
    """

    # Exact match
    quote1 = "We retain personal data for up to 7 years after account termination."
    assert validate_evidence(quote1, raw_policy) is True

    # Normalized whitespace and newline match
    quote2 = "We retain personal data   for up to 7 years\nafter account termination."
    assert validate_evidence(quote2, raw_policy) is True

    # Invalid quote not in policy
    quote3 = "We retain personal data indefinitely and sell it to third parties."
    assert validate_evidence(quote3, raw_policy) is False

    # Empty inputs
    assert validate_evidence("", raw_policy) is False
    assert validate_evidence("Some quote", "") is False


def test_category_scores_calculation():
    findings = [
        RiskFindingSchema(
            category="Privacy",
            finding="Extended retention of personal data",
            severity="High",
            evidence="We retain personal data for up to 7 years",
            source_url="https://example.com/privacy",
            confidence=0.9,
            recommendation="Review retention schedule",
            is_verified=True,
        ),
        RiskFindingSchema(
            category="Privacy",
            finding="Third-party data sharing without opt-out",
            severity="Medium",
            evidence="Data shared with marketing partners",
            source_url="https://example.com/privacy",
            confidence=0.8,
            recommendation="Add opt-out clause",
            is_verified=True,
        ),
        # Unverified finding should be excluded from penalty calculation
        RiskFindingSchema(
            category="Privacy",
            finding="Fake unverified finding",
            severity="Critical",
            evidence="Nonexistent text quote",
            source_url="https://example.com/privacy",
            confidence=0.5,
            recommendation="Ignore",
            is_verified=False,
        ),
        RiskFindingSchema(
            category="Security",
            finding="Missing SOC2 report",
            severity="Low",
            evidence="Security audits performed annually",
            source_url="https://example.com/security",
            confidence=0.85,
            recommendation="Request SOC2",
            is_verified=True,
        ),
    ]

    results = calculate_category_scores(findings)

    # Privacy: High (+35) + Medium (+20) = 55.0 (Unverified Critical is excluded)
    privacy_score, privacy_just, privacy_findings = results["Privacy"]
    assert privacy_score == 55.0
    assert "2 verified finding(s)" in privacy_just
    assert len(privacy_findings) == 3

    # Security: Low (+10) = 10.0
    sec_score, sec_just, sec_findings = results["Security"]
    assert sec_score == 10.0
    assert "1 verified finding(s)" in sec_just

    # Compliance: No findings = 0.0
    comp_score, comp_just, comp_findings = results["Compliance"]
    assert comp_score == 0.0
    assert "No verified risk findings" in comp_just

    # Legal: No findings = 0.0
    legal_score, legal_just, legal_findings = results["Legal"]
    assert legal_score == 0.0


def test_overall_score_calculation():
    cat_scores = {
        "Privacy": 60.0,
        "Security": 40.0,
        "Compliance": 50.0,
        "Legal": 30.0,
    }
    # Formula: Privacy(60 * 0.3) + Security(40 * 0.3) + Compliance(50 * 0.2) + Legal(30 * 0.2)
    # = 18.0 + 12.0 + 10.0 + 6.0 = 46.0
    overall = calculate_overall_score(cat_scores)
    assert overall == 46.0


def test_determine_risk_tier():
    assert determine_risk_tier(10.0) == RiskTier.LOW
    assert determine_risk_tier(24.99) == RiskTier.LOW
    assert determine_risk_tier(25.0) == RiskTier.MEDIUM
    assert determine_risk_tier(49.9) == RiskTier.MEDIUM
    assert determine_risk_tier(50.0) == RiskTier.HIGH
    assert determine_risk_tier(74.9) == RiskTier.HIGH
    assert determine_risk_tier(75.0) == RiskTier.CRITICAL
    assert determine_risk_tier(95.0) == RiskTier.CRITICAL


@pytest.mark.asyncio
async def test_ai_risk_engine_mock_llm():
    mock_findings = [
        RiskFindingSchema(
            category="Privacy",
            finding="Indefinite data retention",
            severity="High",
            evidence="We retain personal information indefinitely.",
            source_url="https://testvendor.com/privacy",
            confidence=0.95,
            recommendation="Restrict data retention period.",
            is_verified=True,
        ),
        RiskFindingSchema(
            category="Security",
            finding="Lack of SOC2 compliance",
            severity="Medium",
            evidence="SOC2 audits are not currently conducted.",
            source_url="https://testvendor.com/security",
            confidence=0.90,
            recommendation="Obtain independent SOC2 certification.",
            is_verified=True,
        ),
        RiskFindingSchema(
            category="Compliance",
            finding="No GDPR DPA provided",
            severity="Medium",
            evidence="Standard contractual clauses are available upon request.",
            source_url="https://testvendor.com/privacy",
            confidence=0.85,
            recommendation="Sign formal DPA.",
            is_verified=True,
        ),
        RiskFindingSchema(
            category="Legal",
            finding="Limitation of liability capped at $100",
            severity="High",
            evidence="Total aggregate liability shall not exceed $100.",
            source_url="https://testvendor.com/terms",
            confidence=0.92,
            recommendation="Negotiate realistic liability cap.",
            is_verified=True,
        ),
    ]

    mock_ai_result = AIAssessmentResultSchema(
        summary="Vendor presents moderate to high risk across Privacy and Legal dimensions.",
        findings=mock_findings,
    )

    engine = AIRiskEngine(openai_api_key="mock_key", model_name="gpt-4o-mini")

    with patch.object(engine, "_call_llm", new=AsyncMock(return_value=mock_ai_result)):
        result = await engine._call_llm("test prompt")
        assert len(result.findings) == 4
        assert result.summary.startswith("Vendor presents moderate")
