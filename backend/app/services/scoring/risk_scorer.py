def calculate_risk(analysis: str):
    """
    Calculates a simple vendor risk score
    based on keywords in the AI analysis.
    """

    analysis = analysis.lower()

    score = 0

    if "high" in analysis:
        score += 40

    if "medium" in analysis:
        score += 20

    if "low" in analysis:
        score += 10

    if score >= 40:
        level = "High"

    elif score >= 20:
        level = "Medium"

    else:
        level = "Low"

    return {
        "risk_score": score,
        "risk_level": level
    }