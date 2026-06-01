def calculate_user_status(points: int) -> str:
    """Calculate user status based on points. Returns string value."""
    if points >= 121:
        return "PLATINUM"
    elif points >= 51:
        return "GOLD"
    elif points >= 16:
        return "SILVER"
    else:
        return "BRONZE"


def get_status_emoji(status) -> str:
    """Get status emoji. Accepts both string and enum."""
    status_str = status.value if hasattr(status, 'value') else str(status)
    emojis = {
        "BRONZE": "\U0001f949",
        "SILVER": "\U0001f948",
        "GOLD": "\U0001f947",
        "PLATINUM": "\U0001f48e"
    }
    return emojis.get(status_str, "")


def get_status_name_uz(status) -> str:
    """Get status name in Uzbek. Accepts both string and enum."""
    status_str = status.value if hasattr(status, 'value') else str(status)
    names = {
        "BRONZE": "Bronza",
        "SILVER": "Kumush",
        "GOLD": "Oltin",
        "PLATINUM": "Platinum"
    }
    return names.get(status_str, "Noma'lum")


def get_status_benefits(status) -> str:
    """Get status benefits text. Accepts both string and enum."""
    status_str = status.value if hasattr(status, 'value') else str(status)
    benefits = {
        "BRONZE": "Barcha ochiq tadbirlarga kirish huquqi",
        "SILVER": "Klub tadbirlarida oldingi qatorlar\nMaxsus sovg'alar",
        "GOLD": "Yopiq VIP tadbirlarga bepul kirish\nPrezident bilan uchrashuv\nPremium materiallar",
        "PLATINUM": "Bosh Prezident bilan yopiq tushliklar\nMaxsus networking imkoniyatlari\nEksklyuziv sovg'alar va sertifikatlar"
    }
    return benefits.get(status_str, "")
