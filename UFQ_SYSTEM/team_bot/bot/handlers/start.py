from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from bot.database.db import get_user, use_invite_atomic, create_user
from bot.config import ADMIN_ID
from bot.keyboards.reply import bp_main_keyboard, cp_main_keyboard, member_main_keyboard

start_router = Router()

@start_router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        await message.answer("👑 Xush kelibsiz, Bosh Prezident!", reply_markup=bp_main_keyboard())
        return

    user = await get_user(user_id)
    if user:
        if user['is_cp']: await message.answer("👔 Klub Prezidenti paneliga xush kelibsiz!", reply_markup=cp_main_keyboard())
        else: await message.answer("👥 Jamoa a'zosi paneliga xush kelibsiz!", reply_markup=member_main_keyboard())
        return

    if not command.args:
        return await message.answer("⛔ Tizimga kirish uchun Taklifnoma (Invite link) kerak.")

    invite_code = command.args
    invite = await use_invite_atomic(invite_code)
    
    if not invite:
        return await message.answer("❌ Taklifnoma xato yoki allaqachon ishlatilgan!")
    
    target_type, club_id, role_id = invite['target_type'], invite['club_id'], invite['role_id']
    is_cp = True if target_type == 'cp' else False
    
    await create_user(user_id, message.from_user.full_name, club_id, role_id, is_cp)
    
    if is_cp: await message.answer("🎉 Siz Klub Prezidenti (CP) etib tayinlandingiz!", reply_markup=cp_main_keyboard())
    else: await message.answer("🎉 UFQ Jamoasiga xush kelibsiz!", reply_markup=member_main_keyboard())

@start_router.message(F.text == "/cancel")
async def cmd_cancel(message: Message, state):
    await state.clear()
    await message.answer("Jarayon bekor qilindi.")
