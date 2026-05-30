from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def bp_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏢 Klublar"), KeyboardButton(text="👑 Taklifnoma (Invite)")],
            [KeyboardButton(text="🧑‍💻 Barcha a'zolar"), KeyboardButton(text="👥 Jamoa statistikasi")],
            [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="📋 Topshiriq berish")],
            [KeyboardButton(text="⚙️ Sozlamalar")]
        ], resize_keyboard=True
    )

def cp_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎭 Lavozimlar"), KeyboardButton(text="🤝 Jamoa yig'ish")],
            [KeyboardButton(text="👥 Mening Jamoam"), KeyboardButton(text="📢 Ommaviy xabar")],
            [KeyboardButton(text="📋 Topshiriq berish"), KeyboardButton(text="📤 Bergan topshiriqlarim")]
        ], resize_keyboard=True
    )

def member_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📌 Mening Lavozimim"), KeyboardButton(text="📋 Topshiriqlarim")],
            [KeyboardButton(text="🏆 Liderlar taxtasi"), KeyboardButton(text="💬 Prezidentga xat")]
        ], resize_keyboard=True
    )
