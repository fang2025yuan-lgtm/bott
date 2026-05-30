from aiogram import Router, F
from aiogram.types import Message
from bot.database.crud import get_top_users, get_user_results, get_user_by_tg_id
from bot.utils.status_manager import get_status_emoji, get_status_name_uz, get_status_benefits
import html

user_router = Router()


@user_router.message(F.text == "Liderlar Taxtasi")
async def show_leaderboard(message: Message):
    users = await get_top_users(10)

    if not users:
        return await message.answer("Hozircha tizimda faol a'zolar yo'q.")

    text = "<b>TOP-10 Liderlar:</b>\n\n"
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]

    rank = 0
    for user in users:
        rank += 1
        medal = medals[rank - 1] if rank <= 3 else f"{rank}."
        status_emoji = get_status_emoji(user.get('user_status', 'BRONZE'))
        text += f"{medal} {status_emoji} <b>{html.escape(user['full_name'])}</b> - {user.get('total_points', 0)} ball\n"

    await message.answer(text, parse_mode="HTML")


@user_router.message(F.text == "Mening Natijalarim")
async def show_my_results(message: Message):
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        return await message.answer("Siz botda ro'yxatdan o'tmagansiz. /start bosing.")

    points, attended = await get_user_results(message.from_user.id)

    user_status = user.get('user_status', 'BRONZE')
    status_emoji = get_status_emoji(user_status)
    status_name = get_status_name_uz(user_status)
    benefits = get_status_benefits(user_status)

    text = f"<b>Sizning Natijalaringiz:</b>\n\n"
    text += f"<b>Ism:</b> {html.escape(user['full_name'])}\n"
    text += f"<b>Status:</b> {status_emoji} {status_name}\n"
    text += f"<b>Jami ballar:</b> {points}\n"
    text += f"<b>Qatnashgan tadbirlar:</b> {attended} ta\n\n"
    text += f"<b>Imtiyozlar:</b>\n{benefits}\n\n"

    # Show progress to next status
    if user_status == "BRONZE":
        text += f"<i>Keyingi status (Kumush) uchun yana {16 - points} ball kerak.</i>"
    elif user_status == "SILVER":
        text += f"<i>Keyingi status (Oltin) uchun yana {51 - points} ball kerak.</i>"
    elif user_status == "GOLD":
        text += f"<i>Keyingi status (Platinum) uchun yana {121 - points} ball kerak.</i>"
    else:
        text += f"<i>Siz eng yuqori darajada turibsiz!</i>"

    await message.answer(text, parse_mode="HTML")
