from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import html
import logging

from bot.database.db import get_user_full, get_member_tasks, get_task, submit_task, get_leaderboard, get_user, get_cp_of_club
from bot.keyboards.inline import member_tasks_keyboard, task_action_keyboard, review_submission_keyboard

member_router = Router()
logger = logging.getLogger(__name__)

class MemberState(StatesGroup):
    send_message = State()
    submit_task = State()

@member_router.message(F.text == "📌 Mening Lavozimim")
async def show_my_profile(message: Message):
    user = await get_user_full(message.from_user.id)
    if user:
        r_name = user['role_name'] if user['role_name'] else ("Prezident" if user['is_cp'] else "A'zo")
        await message.answer(f"👤 <b>Ism:</b> {html.escape(user['full_name'])}\n👔 <b>Lavozim:</b> {html.escape(r_name)}\n🏅 <b>Sizning ballingiz:</b> {user['score']}\n\nTopshiriqlarni bajarib ballaringizni oshiring!", parse_mode="HTML")
    else:
        await message.answer("Siz tizimda yo'qsiz. Taklifnoma oling.")

@member_router.message(F.text == "📋 Topshiriqlarim")
async def my_tasks(message: Message):
    user = await get_user(message.from_user.id)
    if not user: return await message.answer("Siz tizimda yo'qsiz.")
    tasks = await get_member_tasks(user['telegram_id'], user['club_id'], user['is_cp'])
    if tasks: 
        await message.answer("👇 Sizning faol topshiriqlaringiz:", reply_markup=member_tasks_keyboard(tasks))
    else: 
        await message.answer("Hozircha faol topshiriqlar yo'q! Dam oling 😊")

@member_router.callback_query(F.data.startswith("task_"))
async def show_specific_task(call: CallbackQuery):
    task_id = int(call.data.split("_")[1])
    task = await get_task(task_id)
    if task:
        await call.message.answer(f"📋 <b>{html.escape(task['title'])}</b>\n\n{html.escape(task['description'])}", parse_mode="HTML", reply_markup=task_action_keyboard(task_id))
    await call.answer()

@member_router.callback_query(F.data.startswith("submit_task_"))
async def prompt_submit_task(call: CallbackQuery, state: FSMContext):
    task_id = int(call.data.split("_")[2])
    await state.update_data(task_id=task_id)
    await call.message.answer("📥 Ushbu topshiriq bo'yicha hisobot/dalil matnini yuboring. (Bekor qilish: /cancel)")
    await state.set_state(MemberState.submit_task)
    await call.answer()

@member_router.message(MemberState.submit_task)
async def process_submit_task(message: Message, state: FSMContext):
    try:
        if not message.text:
            return await message.answer("Iltimos, matn yuboring (/cancel)")
        if message.text == '/cancel':
            return await message.answer("Bekor qilindi.")
        
        user = await get_user(message.from_user.id)
        if not user: return await message.answer("Siz tizimda yo'qsiz.")
        
        data = await state.get_data()
        task_id = data['task_id']
        task = await get_task(task_id)
        
        sub_id = await submit_task(task_id, user['telegram_id'], message.text)
        if sub_id == -1:
            await message.answer("⚠️ Siz bu topshiriqni allaqachon yuborgansiz (Kutish jarayonida yoki Qabul qilingan)!")
        else:
            await message.answer("✅ Dalil yuborildi! U endi 'Topshiriqlarim' qutisidan yo'qoladi. Prezident tasdiqlashini kuting.")
            if task and task['created_by_telegram_id']:
                try:
                    safe_title = html.escape(task['title'])
                    safe_proof = html.escape(message.text)
                    from bot.keyboards.inline import review_submission_keyboard
                    await message.bot.send_message(
                        task['created_by_telegram_id'], 
                        f"📥 <b>Yangi Topshiriq Javobi:</b>\nA'zo: {html.escape(user['full_name'])}\nTopshiriq: {safe_title}\nJavob: {safe_proof}", 
                        parse_mode="HTML",
                        reply_markup=review_submission_keyboard(sub_id, user['telegram_id'])
                    )
                except Exception as e: logger.error(f"Topshiriq javobi xabari yuborishda xatolik: {e}")
    finally:
        await state.clear()

@member_router.message(F.text == "🏆 Liderlar taxtasi")
async def leaderboard(message: Message):
    user = await get_user(message.from_user.id)
    if not user: return
    board = await get_leaderboard(user['club_id'])
    text = "🏆 <b>Klub Liderlari:</b>\n\n"
    for idx, member in enumerate(board, 1): text += f"{idx}. {html.escape(member['full_name'])} - {member['score']} ball\n"
    await message.answer(text, parse_mode="HTML")

@member_router.message(F.text == "💬 Prezidentga xat")
async def message_cp(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user: return
    await message.answer("✏️ Klub Prezidentiga qanday xabar yubormoqchisiz? Shuni yozing (Bekor qilish: /cancel):")
    await state.set_state(MemberState.send_message)

@member_router.message(MemberState.send_message)
async def process_msg_cp(message: Message, state: FSMContext):
    try:
        if not message.text:
            return await message.answer("Iltimos, matn yuboring (/cancel)")
        if message.text == '/cancel':
            return await message.answer("Bekor qilindi.")
        user = await get_user(message.from_user.id)
        if not user: return await message.answer("Siz tizimda yo'qsiz.")
        
        cp_id = await get_cp_of_club(user['club_id'])
        if cp_id:
            try:
                safe_text = html.escape(message.text)
                await message.bot.send_message(cp_id, f"📩 <b>A'zodan xat:</b>\nKimdan: {html.escape(user['full_name'])}\n\nXabar: {safe_text}", parse_mode="HTML")
                await message.answer("✅ Xabar Prezidentga yuborildi!")
            except Exception as e:
                logger.error(f"Prezidentga xat yuborishda xatolik: {e}")
                await message.answer("Xatolik: Prezident botni bloklagan bo'lishi mumkin.")
        else: await message.answer("Klubingizda hozircha Prezident yo'q.")
    finally:
        await state.clear()

# Global cancel handler
@member_router.message(F.text == "/cancel")
async def global_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Barcha joriy amallar bekor qilindi.")
