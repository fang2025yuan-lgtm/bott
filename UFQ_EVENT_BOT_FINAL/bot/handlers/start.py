from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import html

from bot.database.crud import get_user_by_tg_id, create_user, get_all_clubs, update_user_role
from bot.database.models import RoleEnum
from bot.keyboards.menus import main_menu_keyboard, clubs_inline_keyboard
from bot.config import SUPER_ADMIN_ID

start_router = Router()

class RegState(StatesGroup):
    waiting_for_name = State()

@start_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command=None):
    user = await get_user_by_tg_id(message.from_user.id)
    
    if message.from_user.id == SUPER_ADMIN_ID:
        if user and user.role != RoleEnum.SUPER_ADMIN:
            await update_user_role(user.telegram_id, RoleEnum.SUPER_ADMIN)
            user.role = RoleEnum.SUPER_ADMIN

    if user:
        await message.answer(f"👋 Xush kelibsiz qaytib, {html.escape(user.full_name)}!", reply_markup=main_menu_keyboard(user.role.value))
    else:
        if message.from_user.id == SUPER_ADMIN_ID:
            user = await create_user(telegram_id=message.from_user.id, full_name=message.from_user.full_name or "Super Admin", role=RoleEnum.SUPER_ADMIN)
            await message.answer("Siz Super Admin sifatida ro'yxatdan o'tdingiz!", reply_markup=main_menu_keyboard(user.role.value))
            return
            
        await message.answer("👋 UFQ Botiga xush kelibsiz!\nIltimos, ism-familiyangizni to'liq kiriting:")
        await state.set_state(RegState.waiting_for_name)

@start_router.message(RegState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    if not message.text: return await message.answer("Iltimos, matn yuboring.")
    await state.update_data(full_name=message.text)
    
    clubs = await get_all_clubs()
    if not clubs:
        role = RoleEnum.SUPER_ADMIN if message.from_user.id == SUPER_ADMIN_ID else RoleEnum.USER
        user = await create_user(telegram_id=message.from_user.id, full_name=message.text, username=message.from_user.username, role=role)
        await message.answer("Profil yaratildi! (Hozircha klublar yo'q)", reply_markup=main_menu_keyboard(user.role.value))
        await state.clear()
        return

    await message.answer(f"Rahmat, {html.escape(message.text)}!\nQaysi klubga a'zosiz?", reply_markup=clubs_inline_keyboard(clubs))

@start_router.callback_query(F.data.startswith("joinclub_"))
async def process_club_selection(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_")
    if len(parts) < 2:
        return await call.answer("Noto'g'ri ma'lumot", show_alert=True)
    
    try:
        club_id = int(parts[1])
    except (ValueError, IndexError):
        return await call.answer("Klub ID noto'g'ri", show_alert=True)
    
    data = await state.get_data()
    full_name = data.get("full_name", call.from_user.full_name)
    
    role = RoleEnum.SUPER_ADMIN if call.from_user.id == SUPER_ADMIN_ID else RoleEnum.USER
    user = await create_user(telegram_id=call.from_user.id, full_name=full_name, username=call.from_user.username, club_id=club_id, role=role)

    await call.message.edit_text("🎉 Ajoyib! Profilingiz muvaffaqiyatli yaratildi va klubga biriktirildi.")
    await call.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard(user.role.value))
    await state.clear()
    await call.answer()

