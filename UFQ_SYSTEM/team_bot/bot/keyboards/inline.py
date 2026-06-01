from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def clubs_inline_keyboard(clubs, action="club"):
    keyboard = [[InlineKeyboardButton(text=club['name'], callback_data=f"{action}_{club['id']}")] for club in clubs]
    if action == "club":
        keyboard.append([InlineKeyboardButton(text="➕ Yangi klub qo'shish", callback_data="add_club")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def clubs_invite_keyboard(clubs):
    keyboard = [[InlineKeyboardButton(text=club['name'], callback_data=f"invite_club_{club['id']}")] for club in clubs]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def target_group_keyboard(prefix):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Butun UFQ Jamoasiga", callback_data=f"{prefix}tgt_all")],
        [InlineKeyboardButton(text="👔 Hamma Prezidentlarga", callback_data=f"{prefix}tgt_cps")]
    ])

def target_cp_group_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌍 Umumiy Jamoaga", callback_data="cp_tgt_club")],
        [InlineKeyboardButton(text="👤 Individual", callback_data="cp_tgt_ind")]
    ])

def members_inline_keyboard(members, action="kick"):
    keyboard = []
    for m in members:
        icon = "👔" if m['is_cp'] else "👤"
        keyboard.append([InlineKeyboardButton(text=f"{icon} {m['full_name']}", callback_data=f"{action}_{m['telegram_id']}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def club_manage_keyboard(club_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nomini tahrirlash", callback_data=f"edit_club_{club_id}")],
        [InlineKeyboardButton(text="❌ Klubni o'chirish", callback_data=f"del_club_{club_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_clubs")]
    ])

def role_manage_keyboard(role_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ O'chirish", callback_data=f"del_role_{role_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_roles")]
    ])

def cp_roles_keyboard(roles):
    keyboard = [[InlineKeyboardButton(text=f"👔 {role['name']}", callback_data=f"role_{role['id']}")] for role in roles]
    keyboard.append([InlineKeyboardButton(text="➕ Yangi Lavozim qo'shish", callback_data="add_role")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def roles_invite_keyboard(roles):
    keyboard = [[InlineKeyboardButton(text=f"👔 {role['name']}", callback_data=f"invite_role_{role['id']}")] for role in roles]
    keyboard.append([InlineKeyboardButton(text="👤 Oddiy a'zo (Rolsiz)", callback_data="invite_role_0")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def member_tasks_keyboard(tasks):
    keyboard = []
    for task in tasks:
        prefix = "❌ " if task['status'] == 'rejected' else "📋 "
        keyboard.append([InlineKeyboardButton(text=f"{prefix}{task['title']}", callback_data=f"task_{task['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def task_action_keyboard(task_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Bajarish (Dalil yuklash)", callback_data=f"submit_task_{task_id}")]
    ])

def review_submission_keyboard(sub_id, telegram_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Qabul qilish (+10 ball)", callback_data=f"approve_{sub_id}_{telegram_id}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{sub_id}_{telegram_id}")]
    ])
