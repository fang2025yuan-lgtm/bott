from bot.database.models import UserStatus

def calculate_user_status(points: int) -> UserStatus:
    """Ball asosida foydalanuvchi statusini aniqlash"""
    if points >= 121:
        return UserStatus.PLATINUM
    elif points >= 51:
        return UserStatus.GOLD
    elif points >= 16:
        return UserStatus.SILVER
    else:
        return UserStatus.BRONZE

def get_status_emoji(status: UserStatus) -> str:
    """Status uchun emoji qaytarish"""
    status_emojis = {
        UserStatus.BRONZE: "🥉",
        UserStatus.SILVER: "🥈",
        UserStatus.GOLD: "🥇",
        UserStatus.PLATINUM: "💎"
    }
    return status_emojis.get(status, "")

def get_status_name_uz(status: UserStatus) -> str:
    """Status nomini o'zbekcha qaytarish"""
    status_names = {
        UserStatus.BRONZE: "Bronza",
        UserStatus.SILVER: "Kumush",
        UserStatus.GOLD: "Oltin",
        UserStatus.PLATINUM: "Platinum"
    }
    return status_names.get(status, "Noma'lum")

def get_status_benefits(status: UserStatus) -> str:
    """Status imtiyozlarini matn sifatida qaytarish"""
    benefits = {
        UserStatus.BRONZE: "• Barcha ochiq tadbirlarga kirish huquqi",
        UserStatus.SILVER: "• Klub tadbirlarida oldingi qatorlar\n• Maxsus sovg'alar",
        UserStatus.GOLD: "• Yopiq VIP tadbirlarga bepul kirish\n• Prezident bilan uchrashuv\n• Premium materiallar",
        UserStatus.PLATINUM: "• Bosh Prezident bilan yopiq tushliklar\n• Maxsus networking imkoniyatlari\n• Eksklyuziv sovg'alar va sertifikatlar"
    }
    return benefits.get(status, "")
