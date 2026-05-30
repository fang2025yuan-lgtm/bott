from aiogram import Router, F
from aiogram.types import Message
from bot.database.crud import get_top_users, get_user_results
from bot.database.models import RoleEnum
import html

user_router = Router()

@user_router.message(F.text == "🏆 Liderlar Taxtasi")
async def show_leaderboard(message: Message):
    users = await get_top_users(10)
    
    if not users:
        return await message.answer("Hozircha tizimda faol a'zolar yo'q.")
        
    text = "🏆 <b>TOP-10 Liderlar:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    rank = 0
    for user in users:
        rank += 1
        medal = medals[rank-1] if rank <= 3 else f"{rank}."
        text += f"{medal} <b>{html.escape(user.full_name)}</b> - {user.total_points} ball\n"
        
    await message.answer(text, parse_mode="HTML")

@user_router.message(F.text == "👤 Mening Natijalarim")
async def show_my_results(message: Message):
    points, attended = await get_user_results(message.from_user.id)
    
    text = f"👤 <b>Sizning Natijalaringiz:</b>\n\n"
    text += f"🏅 <b>Jami ballar:</b> {points}\n"
    text += f"📅 <b>Qatnashgan tadbirlar:</b> {attended} ta\n\n"
    text += "<i>Tadbirlarga ro'yxatdan o'ting va qatnashing. Ballaringizni oshirib boring!</i>"
    
    await message.answer(text, parse_mode="HTML")
