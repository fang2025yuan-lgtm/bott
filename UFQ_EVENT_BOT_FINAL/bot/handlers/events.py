from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from bot.database.crud import get_active_events, register_user_for_event
from bot.keyboards.menus import event_registration_keyboard
import html

events_router = Router()

@events_router.message(F.text == "📅 Faol Tadbirlar")
async def show_active_events(message: Message):
    events = await get_active_events(limit=10)
    
    if not events:
        return await message.answer("😔 Hozircha ochiq (faol) tadbirlar yo'q.")
        
    await message.answer("👇 Quyida faol tadbirlar ro'yxati keltirilgan (eng so'nggi 10 ta):")
    
    import asyncio
    for i, event in enumerate(events):
        desc = html.escape(event.description) if event.description else "Tavsif yo'q"
        text = f"🎯 <b>{html.escape(event.title)}</b>\n\n📝 {desc}\n🎁 <i>Ro'yxatdan o'tish: +{event.registration_points} ball</i>\n🏆 <i>Qatnashish: +{event.attendance_points} ball</i>"
        await message.answer(text, reply_markup=event_registration_keyboard(event.id, event.post_link), parse_mode="HTML")
        # Telegram rate limit oldini olish
        if (i + 1) % 20 == 0:
            await asyncio.sleep(1)

@events_router.callback_query(F.data.startswith("reg_event_"))
async def register_to_event(call: CallbackQuery):
    parts = call.data.split("_")
    if len(parts) < 3:
        return await call.answer("Noto'g'ri ma'lumot", show_alert=True)
    
    try:
        event_id = int(parts[2])
    except (ValueError, IndexError):
        return await call.answer("Tadbir ID noto'g'ri", show_alert=True)
    
    success, msg = await register_user_for_event(call.from_user.id, event_id)
    
    if success:
        await call.message.edit_reply_markup(reply_markup=None)
        await call.answer("✅ Ro'yxatdan o'tdingiz!", show_alert=True)
    else:
        await call.answer(msg, show_alert=True)
