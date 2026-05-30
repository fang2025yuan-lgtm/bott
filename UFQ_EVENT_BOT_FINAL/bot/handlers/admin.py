from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database.crud import get_active_events, get_event_registrations, mark_attendance, create_event, get_user_by_tg_id, create_club, promote_user
from bot.database.models import RegStatus
from bot.keyboards.menus import admin_events_keyboard, attendance_keyboard
from bot.config import SUPER_ADMIN_ID
import html

admin_router = Router()

class EventState(StatesGroup):
    waiting_for_title = State()
    waiting_for_desc = State()
    waiting_for_link = State()
    waiting_for_reg_pts = State()
    waiting_for_att_pts = State()

class ClubState(StatesGroup):
    waiting_for_name = State()

class PromoteState(StatesGroup):
    waiting_for_id = State()

async def check_admin(user_id: int, allowed_roles: list, club_id_needed: int = None):
    user = await get_user_by_tg_id(user_id)
    if not user or user.role.value not in allowed_roles:
        return False
    if user.role.value == 'SUPER_ADMIN':
        return True
    if club_id_needed and user.club_id != club_id_needed:
        return False
    return True

@admin_router.message(F.text == "⚙️ Super Admin Panel")
async def super_admin_panel(message: Message):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    text = "⚙️ <b>SUPER ADMIN PANEL</b>\n\nQuyidagi komandalardan foydalaning:\n"
    text += "<code>/add_club</code> - Yangi klub ochish\n"
    text += "<code>/promote</code> - Foydalanuvchiga rahbarlik berish (VP/President)"
    await message.answer(text, parse_mode="HTML")

@admin_router.message(F.text == "/add_club")
async def add_club_cmd(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    await message.answer("Yangi klub nomini yozing (Bekor qilish: /cancel):")
    await state.set_state(ClubState.waiting_for_name)

@admin_router.message(ClubState.waiting_for_name)
async def process_club_name(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    
    club, msg = await create_club(message.text)
    if club:
        await message.answer(f"✅ '{message.text}' klubi yaratildi!")
    else:
        await message.answer(f"❌ Xatolik: {msg}")
    await state.clear()

@admin_router.message(F.text == "/promote")
async def promote_cmd(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    await message.answer("Foydalanuvchining Telegram ID raqamini va Bo'sh joy bilan lavozimni yozing.\nMisol: <code>123456789 PRESIDENT</code> yoki <code>123456789 VP</code> (Bekor qilish: /cancel)", parse_mode="HTML")
    await state.set_state(PromoteState.waiting_for_id)

@admin_router.message(PromoteState.waiting_for_id)
async def process_promote(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    try:
        parts = message.text.split()
        target_id = int(parts[0])
        role_name = parts[1].upper()
        if role_name not in ['VP', 'PRESIDENT']: raise ValueError()
        
        success, msg = await promote_user(target_id, role_name)
        await message.answer(msg)
    except Exception:
        await message.answer("Xatolik! Formatni to'g'ri kiriting: ID ROLE")
    finally:
        await state.clear()

@admin_router.message(F.text == "🛡 Klub Boshqaruvi")
async def show_admin_panel(message: Message):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): return
    events = await get_active_events()
    await message.answer("Boshqarish uchun tadbirni tanlang (yoki yangi yarating):", reply_markup=admin_events_keyboard(events))

@admin_router.callback_query(F.data.startswith("manage_event_"))
async def manage_specific_event(call: CallbackQuery):
    parts = call.data.split("_")
    if len(parts) < 3:
        return await call.answer("Noto'g'ri ma'lumot", show_alert=True)
    
    try:
        event_id = int(parts[2])
    except (ValueError, IndexError):
        return await call.answer("Tadbir ID noto'g'ri", show_alert=True)
    
    from bot.database.crud import get_event_by_id
    event = await get_event_by_id(event_id)
    if not event: 
        return await call.answer("Tadbir topilmadi", show_alert=True)
    
    if not await check_admin(call.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN'], event.club_id): 
        return await call.answer("Siz bu tadbirga mas'ul emassiz!", show_alert=True)
        
    registrations = await get_event_registrations(event_id)
    if not registrations:
        return await call.answer("Bu tadbirga hali hech kim ro'yxatdan o'tmagan.", show_alert=True)
        
    await call.message.answer(f"📋 <b>Davomat (Event ID: {event_id}):</b>", parse_mode="HTML")
    for row in registrations:
        reg, user = row[0], row[1]
        text = f"👤 {html.escape(user.full_name)} (@{html.escape(user.username) if user.username else 'yoq'})"
        await call.message.answer(text, reply_markup=attendance_keyboard(reg.id, reg.status))
    await call.answer()

@admin_router.callback_query(F.data.startswith("att_"))
async def process_attendance(call: CallbackQuery):
    parts = call.data.split("_")
    if len(parts) < 3:
        return await call.answer("Noto'g'ri ma'lumot", show_alert=True)
    
    try:
        reg_id = int(parts[1])
        action = parts[2]
    except (ValueError, IndexError):
        return await call.answer("Noto'g'ri parametrlar", show_alert=True)
    
    from bot.database.db import AsyncSessionLocal
    from sqlalchemy.future import select
    from bot.database.models import Registration, Event
    
    async with AsyncSessionLocal() as session:
        reg = (await session.execute(select(Registration).where(Registration.id == reg_id))).scalars().first()
        if not reg: 
            return await call.answer("Ro'yxatdan o'tish topilmadi", show_alert=True)
        event_club_id = (await session.execute(select(Event.club_id).where(Event.id == reg.event_id))).scalars().first()
    
    if not await check_admin(call.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN'], event_club_id): 
        return await call.answer("Xuxuq yo'q", show_alert=True)
    
    new_status = RegStatus.ATTENDED if action == "yes" else RegStatus.ABSENT
    success = await mark_attendance(reg_id, new_status)
    
    if success:
        await call.message.edit_reply_markup(reply_markup=attendance_keyboard(reg_id, new_status))
        await call.answer("Saqlandi!")
    else:
        await call.answer("Holat o'zgarmadi yoki xatolik.", show_alert=True)

@admin_router.callback_query(F.data == "add_new_event")
async def add_event_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): 
        return await call.answer("Xuxuq yo'q", show_alert=True)
        
    await call.message.answer("1️⃣ Yangi tadbir sarlavhasini kiriting (Bekor qilish: /cancel):")
    await state.set_state(EventState.waiting_for_title)
    await call.answer()

@admin_router.message(EventState.waiting_for_title)
async def add_event_title(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    await state.update_data(title=message.text)
    await message.answer("2️⃣ Tadbir uchun to'liq tavsif (description) yozing:")
    await state.set_state(EventState.waiting_for_desc)

@admin_router.message(EventState.waiting_for_desc)
async def add_event_desc(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    await state.update_data(desc=message.text)
    await message.answer("3️⃣ Kanalga tashlangan post havolasini (Link) bering (yoki yo'q bo'lsa '-' qoldiring):")
    await state.set_state(EventState.waiting_for_link)

@admin_router.message(EventState.waiting_for_link)
async def add_event_link(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    link = None if message.text == "-" else message.text
    await state.update_data(link=link)
    await message.answer("4️⃣ Ro'yxatdan o'tish uchun necha ball beriladi? (Raqam yozing, masalan 1):")
    await state.set_state(EventState.waiting_for_reg_pts)

@admin_router.message(EventState.waiting_for_reg_pts)
async def add_event_reg_pts(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    try:
        reg_pts = int(message.text)
        await state.update_data(reg_pts=reg_pts)
        await message.answer("5️⃣ Qatnashganlik (Davomat) uchun necha ball beriladi? (Masalan 5):")
        await state.set_state(EventState.waiting_for_att_pts)
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting!")

@admin_router.message(EventState.waiting_for_att_pts)
async def add_event_att_pts(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    try:
        att_pts = int(message.text)
        data = await state.get_data()
        
        await create_event(
            title=data['title'],
            desc=data['desc'],
            link=data['link'],
            reg_pts=data['reg_pts'],
            att_pts=att_pts,
            created_by_tg_id=message.from_user.id
        )
        
        await message.answer("✅ Tadbir muvaffaqiyatli yaratildi va hamma uchun ochiq!")
        await state.clear()
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting!")
