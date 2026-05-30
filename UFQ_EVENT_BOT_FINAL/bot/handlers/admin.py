from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database.crud import (
    get_active_events, get_event_registrations, mark_attendance, create_event,
    get_user_by_tg_id, create_club, promote_user, get_event_by_id,
    get_all_users, get_all_events, update_event, cancel_event,
    update_user_club, update_user_points, get_club_by_id, delete_club,
    get_all_clubs, get_users_count, get_events_count, get_clubs_count
)
from bot.database.models import RegStatus, EventStatus
from bot.keyboards.menus import (
    admin_events_keyboard, attendance_keyboard,
    super_admin_menu_keyboard, user_management_keyboard,
    event_management_keyboard, sa_users_pagination_keyboard
)
from bot.config import SUPER_ADMIN_ID
from datetime import datetime
import html

admin_router = Router()

class EventState(StatesGroup):
    waiting_for_title = State()
    waiting_for_desc = State()
    waiting_for_link = State()
    waiting_for_reg_pts = State()
    waiting_for_att_pts = State()
    waiting_for_event_date = State()
    waiting_for_location = State()
    waiting_for_check_in = State()

class ClubState(StatesGroup):
    waiting_for_name = State()

class PromoteState(StatesGroup):
    waiting_for_id = State()

class SAEditUserState(StatesGroup):
    waiting_for_tg_id = State()
    waiting_for_club_id = State()
    waiting_for_points = State()
    waiting_for_role = State()

class SAEditEventState(StatesGroup):
    waiting_for_event_id = State()
    waiting_for_title = State()
    waiting_for_points = State()
    waiting_for_status = State()

async def check_admin(user_id: int, allowed_roles: list, club_id_needed: int = None):
    user = await get_user_by_tg_id(user_id)
    if not user or user.role.value not in allowed_roles:
        return False
    if user.role.value == 'SUPER_ADMIN':
        return True
    # Agar klub tekshiruvi zarur bo'lsa va None bo'lmasa
    if club_id_needed is not None and user.club_id != club_id_needed:
        return False
    return True

@admin_router.message(F.text == "⚙️ Super Admin Panel")
async def super_admin_panel(message: Message):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    text = "⚙️ <b>SUPER ADMIN PANEL</b>\n\nQuyidagi komandalardan foydalaning:\n"
    text += "<code>/add_club</code> - Yangi klub ochish\n"
    text += "<code>/promote</code> - Foydalanuvchiga rahbarlik berish (VP/President)\n"
    text += "<code>/users</code> - Barcha foydalanuvchilar ro'yxati\n"
    text += "<code>/user_info &lt;tg_id&gt;</code> - Foydalanuvchi haqida ma'lumot\n"
    text += "<code>/clubs</code> - Barcha klublar ro'yxati\n"
    text += "<code>/events_all</code> - Barcha tadbirlar ro'yxati\n"
    text += "<code>/edit_user &lt;tg_id&gt;</code> - Foydalanuvchini tahrirlash\n"
    text += "<code>/edit_event &lt;event_id&gt;</code> - Tadbirni tahrirlash\n"
    text += "<code>/delete_event &lt;event_id&gt;</code> - Tadbirni bekor qilish\n"
    await message.answer(text, parse_mode="HTML", reply_markup=super_admin_menu_keyboard())

@admin_router.message(Command("add_club"))
async def add_club_cmd(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): 
        return
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

@admin_router.message(Command("promote"))
async def promote_cmd(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): 
        return
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
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): 
        return
    events = await get_active_events(limit=20)
    if not events:
        await message.answer("Hozircha ochiq tadbirlar yo'q. Yangi tadbir yaratishingiz mumkin:", reply_markup=admin_events_keyboard([]))
    else:
        await message.answer("Boshqarish uchun tadbirni tanlang:", reply_markup=admin_events_keyboard(events))

@admin_router.callback_query(F.data.startswith("manage_event_"))
async def manage_specific_event(call: CallbackQuery):
    # Darhol javob berish - loading indicator o'chadi
    await call.answer()
    
    parts = call.data.split("_")
    if len(parts) < 3:
        return await call.message.answer("Noto'g'ri ma'lumot")
    
    try:
        event_id = int(parts[2])
    except (ValueError, IndexError):
        return await call.message.answer("Tadbir ID noto'g'ri")
    
    from bot.database.crud import get_event_by_id
    event = await get_event_by_id(event_id)
    if not event: 
        return await call.message.answer("Tadbir topilmadi")
    
    if not await check_admin(call.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN'], event.club_id): 
        return await call.message.answer("Siz bu tadbirga mas'ul emassiz!")
        
    registrations = await get_event_registrations(event_id)
    if not registrations:
        return await call.message.answer("Bu tadbirga hali hech kim ro'yxatdan o'tmagan.")
        
    await call.message.answer(f"📋 <b>Davomat (Event ID: {event_id}):</b>", parse_mode="HTML")
    
    # Telegram rate limit oldini olish uchun batch yuboring
    import asyncio
    for i, row in enumerate(registrations):
        reg, user = row[0], row[1]
        text = f"👤 {html.escape(user.full_name)} (@{html.escape(user.username) if user.username else 'yoq'})"
        await call.message.answer(text, reply_markup=attendance_keyboard(reg.id, reg.status))
        # Har 20 ta xabardan keyin qisqa pause
        if (i + 1) % 20 == 0:
            await asyncio.sleep(1)

@admin_router.callback_query(F.data.startswith("att_status_"))
async def att_status_info(call: CallbackQuery):
    # Joriy holatni ko'rsatuvchi tugma - faqat ma'lumot berish
    await call.answer("Bu joriy holat. O'zgartirish uchun boshqa tugmani bosing.", show_alert=False)

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
    
    # CRUD orqali event va registration ma'lumotlarini olish
    from bot.database.db import AsyncSessionLocal
    from sqlalchemy.future import select
    from bot.database.models import Registration
    
    async with AsyncSessionLocal() as session:
        reg = (await session.execute(select(Registration).where(Registration.id == reg_id))).scalars().first()
        if not reg: 
            return await call.answer("Ro'yxatdan o'tish topilmadi", show_alert=True)
        event_id = reg.event_id
    
    # Event ma'lumotlarini olish
    event = await get_event_by_id(event_id)
    if not event:
        return await call.answer("Tadbir topilmadi", show_alert=True)
    
    if not await check_admin(call.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN'], event.club_id): 
        return await call.answer("Ruxsat yo'q", show_alert=True)
    
    new_status = RegStatus.ATTENDED if action == "yes" else RegStatus.ABSENT
    success = await mark_attendance(reg_id, new_status)
    
    if success:
        await call.message.edit_reply_markup(reply_markup=attendance_keyboard(reg_id, new_status))
        await call.answer("✅ Saqlandi!")
    else:
        # Holat o'zgarmagan - bu xatolik emas, faqat qayta bosish
        await call.answer("Holat allaqachon shunday o'rnatilgan.", show_alert=False)

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
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): 
        await state.clear()
        return
    if not message.text: 
        return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    try:
        reg_pts = int(message.text)
        if reg_pts < 0:
            return await message.answer("⚠️ Ball manfiy bo'lishi mumkin emas. Iltimos, musbat son kiriting.")
        await state.update_data(reg_pts=reg_pts)
        await message.answer("5️⃣ Qatnashganlik (Davomat) uchun necha ball beriladi? (Masalan 5):")
        await state.set_state(EventState.waiting_for_att_pts)
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting!")

@admin_router.message(EventState.waiting_for_att_pts)
async def add_event_att_pts(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): 
        await state.clear()
        return
    if not message.text: 
        return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    try:
        att_pts = int(message.text)
        if att_pts < 0:
            return await message.answer("⚠️ Ball manfiy bo'lishi mumkin emas. Iltimos, musbat son kiriting.")
        
        await state.update_data(att_pts=att_pts)
        await message.answer("6️⃣ Tadbir sanasi va vaqtini kiriting (Format: DD.MM.YYYY HH:MM) yoki o'tkazib yuborish uchun '-' yozing:")
        await state.set_state(EventState.waiting_for_event_date)
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting!")

@admin_router.message(EventState.waiting_for_event_date)
async def add_event_date(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): 
        await state.clear()
        return
    if not message.text: 
        return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    
    if message.text.strip() == '-':
        event_date = None
    else:
        try:
            event_date = datetime.strptime(message.text.strip(), '%d.%m.%Y %H:%M')
        except ValueError:
            return await message.answer("⚠️ Noto'g'ri format! Iltimos DD.MM.YYYY HH:MM formatida kiriting (masalan: 25.01.2025 14:00) yoki '-' bosing.")
    
    await state.update_data(event_date=event_date)
    await message.answer("7️⃣ Tadbir joylashuvini kiriting (yoki o'tkazib yuborish uchun '-' yozing):")
    await state.set_state(EventState.waiting_for_location)

@admin_router.message(EventState.waiting_for_location)
async def add_event_location(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): 
        await state.clear()
        return
    if not message.text: 
        return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    
    location = None if message.text.strip() == '-' else message.text.strip()
    await state.update_data(location=location)
    await message.answer("8️⃣ QR skanerlash (check-in) yoqilsinmi? (Ha / Yo'q):")
    await state.set_state(EventState.waiting_for_check_in)

@admin_router.message(EventState.waiting_for_check_in)
async def add_event_check_in(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']): 
        await state.clear()
        return
    if not message.text: 
        return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    
    check_in_enabled = message.text.strip().lower() in ['ha', 'yes', 'da']
    
    data = await state.get_data()
    
    success, msg = await create_event(
        title=data['title'],
        desc=data['desc'],
        link=data['link'],
        reg_pts=data['reg_pts'],
        att_pts=data['att_pts'],
        created_by_tg_id=message.from_user.id,
        event_date=data.get('event_date'),
        location=data.get('location'),
        check_in_enabled=check_in_enabled
    )
    
    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ Xatolik: {msg}")
    await state.clear()


# =============================================
# SUPER ADMIN HANDLERS
# =============================================

@admin_router.message(F.text == "📊 Statistika")
async def show_statistics(message: Message):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    users_count = await get_users_count()
    events_count = await get_events_count()
    clubs_count = await get_clubs_count()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{users_count}</b>\n"
        f"📅 Jami tadbirlar: <b>{events_count}</b>\n"
        f"🏢 Jami klublar: <b>{clubs_count}</b>"
    )
    await message.answer(text, parse_mode="HTML")


@admin_router.callback_query(F.data == "sa_stats")
async def sa_stats_callback(call: CallbackQuery):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    users_count = await get_users_count()
    events_count = await get_events_count()
    clubs_count = await get_clubs_count()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{users_count}</b>\n"
        f"📅 Jami tadbirlar: <b>{events_count}</b>\n"
        f"🏢 Jami klublar: <b>{clubs_count}</b>"
    )
    await call.message.answer(text, parse_mode="HTML")


# --- /users command and pagination ---
@admin_router.message(Command("users"))
async def cmd_users(message: Message):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    await _show_users_page(message, page=1)


@admin_router.callback_query(F.data == "sa_users")
async def sa_users_callback(call: CallbackQuery):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    await _show_users_page(call.message, page=1)


@admin_router.callback_query(F.data.startswith("sa_users_page_"))
async def sa_users_page_callback(call: CallbackQuery):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    page = int(call.data.split("_")[-1])
    await _show_users_page(call.message, page=page)


async def _show_users_page(message: Message, page: int):
    per_page = 20
    offset = (page - 1) * per_page
    users = await get_all_users(limit=per_page + 1, offset=offset)
    has_next = len(users) > per_page
    users = users[:per_page]

    if not users:
        return await message.answer("Foydalanuvchilar topilmadi.")

    text = f"👥 <b>Foydalanuvchilar (sahifa {page}):</b>\n\n"
    for i, user in enumerate(users, start=offset + 1):
        username = f"@{html.escape(user.username)}" if user.username else "---"
        text += (
            f"{i}. {html.escape(user.full_name)} | {username}\n"
            f"   ID: <code>{user.telegram_id}</code> | 🎯 {user.total_points} ball | {user.role.value}\n"
        )

    await message.answer(text, parse_mode="HTML", reply_markup=sa_users_pagination_keyboard(page, has_next))


# --- /user_info command ---
@admin_router.message(Command("user_info"))
async def cmd_user_info(message: Message):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Format: <code>/user_info &lt;telegram_id&gt;</code>", parse_mode="HTML")
    try:
        target_tg_id = int(parts[1])
    except ValueError:
        return await message.answer("Telegram ID raqam bo'lishi kerak!")

    user = await get_user_by_tg_id(target_tg_id)
    if not user:
        return await message.answer("Foydalanuvchi topilmadi.")

    from bot.database.crud import get_user_results
    points, attended = await get_user_results(target_tg_id)
    club_name = "---"
    if user.club_id:
        club = await get_club_by_id(user.club_id)
        if club:
            club_name = html.escape(club.club_name)

    text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
        f"📛 Ism: {html.escape(user.full_name)}\n"
        f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"👤 Username: @{html.escape(user.username) if user.username else '---'}\n"
        f"🏢 Klub: {club_name}\n"
        f"👑 Rol: {user.role.value}\n"
        f"🎯 Ballar: {user.total_points}\n"
        f"🏅 Status: {user.user_status.value}\n"
        f"✅ Qatnashgan tadbirlar: {attended}\n"
        f"📅 Ro'yxatdan o'tgan: {user.created_at.strftime('%d.%m.%Y') if user.created_at else '---'}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=user_management_keyboard(user.telegram_id))


# --- /edit_user command ---
@admin_router.message(Command("edit_user"))
async def cmd_edit_user(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Foydalanuvchining Telegram ID sini kiriting (Bekor qilish: /cancel):")
        await state.set_state(SAEditUserState.waiting_for_tg_id)
        return
    try:
        target_tg_id = int(parts[1])
    except ValueError:
        return await message.answer("Telegram ID raqam bo'lishi kerak!")

    user = await get_user_by_tg_id(target_tg_id)
    if not user:
        return await message.answer("Foydalanuvchi topilmadi.")
    await message.answer(
        f"Foydalanuvchi: {html.escape(user.full_name)} (ID: {user.telegram_id})\nQuyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=user_management_keyboard(user.telegram_id)
    )


@admin_router.message(SAEditUserState.waiting_for_tg_id)
async def sa_edit_user_tg_id(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    try:
        target_tg_id = int(message.text.strip())
    except ValueError:
        return await message.answer("Telegram ID raqam bo'lishi kerak!")
    user = await get_user_by_tg_id(target_tg_id)
    if not user:
        await state.clear()
        return await message.answer("Foydalanuvchi topilmadi.")
    await state.clear()
    await message.answer(
        f"Foydalanuvchi: {html.escape(user.full_name)}\nQuyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=user_management_keyboard(user.telegram_id)
    )


# --- User management callbacks ---
@admin_router.callback_query(F.data.startswith("sa_uchg_club_"))
async def sa_user_change_club(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    tg_id = int(call.data.split("_")[-1])
    await state.update_data(target_tg_id=tg_id)
    await state.set_state(SAEditUserState.waiting_for_club_id)
    await call.message.answer("Yangi klub ID raqamini kiriting (Bekor qilish: /cancel):")


@admin_router.message(SAEditUserState.waiting_for_club_id)
async def sa_user_set_club(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    try:
        club_id = int(message.text.strip())
    except ValueError:
        return await message.answer("Klub ID raqam bo'lishi kerak!")
    data = await state.get_data()
    target_tg_id = data['target_tg_id']
    success, msg = await update_user_club(target_tg_id, club_id)
    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")
    await state.clear()


@admin_router.callback_query(F.data.startswith("sa_uchg_pts_"))
async def sa_user_change_points(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    tg_id = int(call.data.split("_")[-1])
    await state.update_data(target_tg_id=tg_id)
    await state.set_state(SAEditUserState.waiting_for_points)
    await call.message.answer("Yangi ball sonini kiriting (Bekor qilish: /cancel):")


@admin_router.message(SAEditUserState.waiting_for_points)
async def sa_user_set_points(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    try:
        points = int(message.text.strip())
        if points < 0:
            return await message.answer("Ball manfiy bo'lishi mumkin emas!")
    except ValueError:
        return await message.answer("Ball raqam bo'lishi kerak!")
    data = await state.get_data()
    target_tg_id = data['target_tg_id']
    success, msg = await update_user_points(target_tg_id, points)
    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")
    await state.clear()


@admin_router.callback_query(F.data.startswith("sa_uchg_role_"))
async def sa_user_change_role(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    tg_id = int(call.data.split("_")[-1])
    await state.update_data(target_tg_id=tg_id)
    await state.set_state(SAEditUserState.waiting_for_role)
    await call.message.answer("Yangi rolni kiriting (USER, VP, PRESIDENT). Bekor qilish: /cancel")


@admin_router.message(SAEditUserState.waiting_for_role)
async def sa_user_set_role(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    data = await state.get_data()
    target_tg_id = data['target_tg_id']
    role_name = message.text.strip().upper()
    if role_name not in ['USER', 'VP', 'PRESIDENT']:
        return await message.answer("Faqat USER, VP, PRESIDENT rollari mumkin!")
    success, msg = await promote_user(target_tg_id, role_name)
    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")
    await state.clear()


# --- /edit_event command ---
@admin_router.message(Command("edit_event"))
async def cmd_edit_event(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Tadbir ID raqamini kiriting (Bekor qilish: /cancel):")
        await state.set_state(SAEditEventState.waiting_for_event_id)
        return
    try:
        event_id = int(parts[1])
    except ValueError:
        return await message.answer("Event ID raqam bo'lishi kerak!")
    event = await get_event_by_id(event_id)
    if not event:
        return await message.answer("Tadbir topilmadi.")
    text = (
        f"📅 <b>{html.escape(event.title)}</b>\n"
        f"ID: {event.id} | Status: {event.status.value}\n"
        f"Reg ball: {event.registration_points} | Att ball: {event.attendance_points}\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=event_management_keyboard(event.id))


@admin_router.message(SAEditEventState.waiting_for_event_id)
async def sa_edit_event_id(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    try:
        event_id = int(message.text.strip())
    except ValueError:
        return await message.answer("Event ID raqam bo'lishi kerak!")
    event = await get_event_by_id(event_id)
    if not event:
        await state.clear()
        return await message.answer("Tadbir topilmadi.")
    await state.clear()
    text = (
        f"📅 <b>{html.escape(event.title)}</b>\n"
        f"ID: {event.id} | Status: {event.status.value}\n"
        f"Reg ball: {event.registration_points} | Att ball: {event.attendance_points}\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=event_management_keyboard(event.id))


# --- Event management callbacks ---
@admin_router.callback_query(F.data.startswith("sa_ev_title_"))
async def sa_event_change_title(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    event_id = int(call.data.split("_")[-1])
    await state.update_data(target_event_id=event_id)
    await state.set_state(SAEditEventState.waiting_for_title)
    await call.message.answer("Yangi sarlavhani kiriting (Bekor qilish: /cancel):")


@admin_router.message(SAEditEventState.waiting_for_title)
async def sa_event_set_title(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    data = await state.get_data()
    event_id = data['target_event_id']
    success, msg = await update_event(event_id, title=message.text.strip())
    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")
    await state.clear()


@admin_router.callback_query(F.data.startswith("sa_ev_pts_"))
async def sa_event_change_points(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    event_id = int(call.data.split("_")[-1])
    await state.update_data(target_event_id=event_id)
    await state.set_state(SAEditEventState.waiting_for_points)
    await call.message.answer("Yangi ballarni kiriting (format: reg_ball att_ball, masalan: 2 10). Bekor qilish: /cancel")


@admin_router.message(SAEditEventState.waiting_for_points)
async def sa_event_set_points(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    try:
        parts = message.text.strip().split()
        reg_pts = int(parts[0])
        att_pts = int(parts[1])
        if reg_pts < 0 or att_pts < 0:
            return await message.answer("Ballar manfiy bo'lishi mumkin emas!")
    except (ValueError, IndexError):
        return await message.answer("Format: reg_ball att_ball (masalan: 2 10)")
    data = await state.get_data()
    event_id = data['target_event_id']
    success, msg = await update_event(event_id, registration_points=reg_pts, attendance_points=att_pts)
    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")
    await state.clear()


@admin_router.callback_query(F.data.startswith("sa_ev_status_"))
async def sa_event_change_status(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    event_id = int(call.data.split("_")[-1])
    await state.update_data(target_event_id=event_id)
    await state.set_state(SAEditEventState.waiting_for_status)
    await call.message.answer("Yangi holatni kiriting (ACTIVE, COMPLETED, CANCELLED). Bekor qilish: /cancel")


@admin_router.message(SAEditEventState.waiting_for_status)
async def sa_event_set_status(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    status_text = message.text.strip().upper()
    if status_text not in ['ACTIVE', 'COMPLETED', 'CANCELLED']:
        return await message.answer("Faqat ACTIVE, COMPLETED, CANCELLED mumkin!")
    data = await state.get_data()
    event_id = data['target_event_id']
    new_status = EventStatus[status_text]
    success, msg = await update_event(event_id, status=new_status)
    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")
    await state.clear()


@admin_router.callback_query(F.data.startswith("sa_ev_cancel_"))
async def sa_event_cancel(call: CallbackQuery):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    event_id = int(call.data.split("_")[-1])
    success, msg = await cancel_event(event_id)
    if success:
        await call.message.answer(f"✅ {msg}")
    else:
        await call.message.answer(f"❌ {msg}")


# --- /delete_event command ---
@admin_router.message(Command("delete_event"))
async def cmd_delete_event(message: Message):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Format: <code>/delete_event &lt;event_id&gt;</code>", parse_mode="HTML")
    try:
        event_id = int(parts[1])
    except ValueError:
        return await message.answer("Event ID raqam bo'lishi kerak!")
    success, msg = await cancel_event(event_id)
    if success:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")


# --- /events_all command ---
@admin_router.message(Command("events_all"))
async def cmd_events_all(message: Message):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    events = await get_all_events(limit=20, offset=0)
    if not events:
        return await message.answer("Tadbirlar topilmadi.")
    text = "📅 <b>Barcha tadbirlar:</b>\n\n"
    for event in events:
        status_emoji = {"ACTIVE": "🟢", "COMPLETED": "✅", "CANCELLED": "❌"}.get(event.status.value, "⚪")
        text += (
            f"{status_emoji} <b>{html.escape(event.title)}</b> (ID: {event.id})\n"
            f"   Status: {event.status.value} | Reg: {event.registration_points} | Att: {event.attendance_points}\n"
        )
    await message.answer(text, parse_mode="HTML")


@admin_router.callback_query(F.data == "sa_events")
async def sa_events_callback(call: CallbackQuery):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    events = await get_all_events(limit=20, offset=0)
    if not events:
        return await call.message.answer("Tadbirlar topilmadi.")
    text = "📅 <b>Barcha tadbirlar:</b>\n\n"
    for event in events:
        status_emoji = {"ACTIVE": "🟢", "COMPLETED": "✅", "CANCELLED": "❌"}.get(event.status.value, "⚪")
        text += (
            f"{status_emoji} <b>{html.escape(event.title)}</b> (ID: {event.id})\n"
            f"   Status: {event.status.value} | Reg: {event.registration_points} | Att: {event.attendance_points}\n"
        )
    await call.message.answer(text, parse_mode="HTML")


# --- /clubs command ---
@admin_router.message(Command("clubs"))
async def cmd_clubs(message: Message):
    if not await check_admin(message.from_user.id, ['SUPER_ADMIN']): return
    await _show_clubs(message)


@admin_router.callback_query(F.data == "sa_clubs")
async def sa_clubs_callback(call: CallbackQuery):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    await _show_clubs(call.message)


async def _show_clubs(message: Message):
    clubs = await get_all_clubs()
    if not clubs:
        return await message.answer("Klublar topilmadi.")
    text = "🏢 <b>Barcha klublar:</b>\n\n"
    for club in clubs:
        member_count = len(club.users) if club.users else 0
        text += f"🏢 <b>{html.escape(club.club_name)}</b> (ID: {club.id})\n   A'zolar: {member_count}\n"
    await message.answer(text, parse_mode="HTML")


# --- sa_edit_user and sa_edit_event callbacks from inline keyboard ---
@admin_router.callback_query(F.data == "sa_edit_user")
async def sa_edit_user_callback(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    await call.message.answer("Foydalanuvchining Telegram ID sini kiriting (Bekor qilish: /cancel):")
    await state.set_state(SAEditUserState.waiting_for_tg_id)


@admin_router.callback_query(F.data == "sa_edit_event")
async def sa_edit_event_callback(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['SUPER_ADMIN']):
        return await call.answer("Ruxsat yo'q", show_alert=True)
    await call.answer()
    await call.message.answer("Tadbir ID raqamini kiriting (Bekor qilish: /cancel):")
    await state.set_state(SAEditEventState.waiting_for_event_id)
