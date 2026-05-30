from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.models import RegStatus

def main_menu_keyboard(role_name):
    kb = [
        [KeyboardButton(text="📅 Faol Tadbirlar"), KeyboardButton(text="🏆 Liderlar Taxtasi")],
        [KeyboardButton(text="👤 Mening Natijalarim")]
    ]
    if role_name in ['VP', 'PRESIDENT', 'SUPER_ADMIN']:
        kb.append([KeyboardButton(text="🛡 Klub Boshqaruvi")])
    if role_name == 'SUPER_ADMIN':
        kb.append([KeyboardButton(text="⚙️ Super Admin Panel"), KeyboardButton(text="📊 Statistika")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def clubs_inline_keyboard(clubs):
    keyboard = [[InlineKeyboardButton(text=club.club_name, callback_data=f"joinclub_{club.id}")] for club in clubs]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def event_registration_keyboard(event_id, post_link):
    kb = [[InlineKeyboardButton(text="✅ Ro'yxatdan O'tish", callback_data=f"reg_event_{event_id}")]]
    if post_link and post_link != "-":
        kb.append([InlineKeyboardButton(text="📢 Kanalda Ko'rish", url=post_link)])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def admin_events_keyboard(events):
    kb = [[InlineKeyboardButton(text=f"📋 {event.title}", callback_data=f"manage_event_{event.id}")] for event in events]
    kb.append([InlineKeyboardButton(text="➕ Yangi Tadbir Yaratish", callback_data="add_new_event")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def attendance_keyboard(reg_id, current_status):
    # Holat indikatorlari va amal tugmalari alohida
    if current_status == RegStatus.ATTENDED:
        # Foydalanuvchi qatnashgan - faqat "Qatnashmadi" deb o'zgartirish mumkin
        kb = [
            [InlineKeyboardButton(text="✅ Qatnashdi (joriy holat)", callback_data=f"att_status_{reg_id}")],
            [InlineKeyboardButton(text="❌ Qatnashmadi deb belgilash", callback_data=f"att_{reg_id}_no")]
        ]
    elif current_status == RegStatus.ABSENT:
        # Foydalanuvchi qatnashmagan - faqat "Qatnashdi" deb o'zgartirish mumkin
        kb = [
            [InlineKeyboardButton(text="✅ Qatnashdi deb belgilash", callback_data=f"att_{reg_id}_yes")],
            [InlineKeyboardButton(text="❌ Qatnashmadi (joriy holat)", callback_data=f"att_status_{reg_id}")]
        ]
    else:
        # REGISTERED - hali davomat belgilanmagan
        kb = [
            [InlineKeyboardButton(text="✅ Qatnashdi", callback_data=f"att_{reg_id}_yes")],
            [InlineKeyboardButton(text="❌ Qatnashmadi", callback_data=f"att_{reg_id}_no")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def super_admin_menu_keyboard():
    """Super admin uchun boshqaruv paneli"""
    kb = [
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="sa_users"),
         InlineKeyboardButton(text="📅 Tadbirlar", callback_data="sa_events")],
        [InlineKeyboardButton(text="🏢 Klublar", callback_data="sa_clubs"),
         InlineKeyboardButton(text="📊 Statistika", callback_data="sa_stats")],
        [InlineKeyboardButton(text="✏️ Foydalanuvchini tahrirlash", callback_data="sa_edit_user")],
        [InlineKeyboardButton(text="✏️ Tadbirni tahrirlash", callback_data="sa_edit_event")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def user_management_keyboard(user_tg_id: int):
    """Foydalanuvchini boshqarish uchun inline tugmalar"""
    kb = [
        [InlineKeyboardButton(text="🔄 Klubni o'zgartirish", callback_data=f"sa_uchg_club_{user_tg_id}")],
        [InlineKeyboardButton(text="🎯 Ballarni o'zgartirish", callback_data=f"sa_uchg_pts_{user_tg_id}")],
        [InlineKeyboardButton(text="⬆️ Rolni o'zgartirish", callback_data=f"sa_uchg_role_{user_tg_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def event_management_keyboard(event_id: int):
    """Tadbirni boshqarish uchun inline tugmalar"""
    kb = [
        [InlineKeyboardButton(text="✏️ Sarlavhani o'zgartirish", callback_data=f"sa_ev_title_{event_id}")],
        [InlineKeyboardButton(text="🎯 Ballarni o'zgartirish", callback_data=f"sa_ev_pts_{event_id}")],
        [InlineKeyboardButton(text="📋 Holatni o'zgartirish", callback_data=f"sa_ev_status_{event_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"sa_ev_cancel_{event_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def sa_users_pagination_keyboard(page: int, has_next: bool):
    """Foydalanuvchilar ro'yxati uchun sahifalash tugmalari"""
    kb = []
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"sa_users_page_{page - 1}"))
    if has_next:
        buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"sa_users_page_{page + 1}"))
    if buttons:
        kb.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=kb)
