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
        kb.append([KeyboardButton(text="⚙️ Super Admin Panel")])
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
    att_text = "✅ Qatnashdi" if current_status == RegStatus.ATTENDED else "✔️ Keldi qilib belgilash"
    abs_text = "❌ Qatnashmadi" if current_status == RegStatus.ABSENT else "✖️ Kelmadi"
    kb = [
        [InlineKeyboardButton(text=att_text, callback_data=f"att_{reg_id}_yes")],
        [InlineKeyboardButton(text=abs_text, callback_data=f"att_{reg_id}_no")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
