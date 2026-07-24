from datetime import datetime


def generate_report(
    vendor,
    privacy_url,
    analysis,
    risk,
    characters_downloaded,
    discovery
):
    return {
        "message": "AI Analysis Completed",
        "vendor": vendor,
        "privacy_policy_url": privacy_url,
        "characters_downloaded": characters_downloaded,
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "analysis": analysis,
        "discovery": discovery,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }