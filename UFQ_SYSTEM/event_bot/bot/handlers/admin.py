from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database.crud import (
    get_active_events, get_event_registrations, mark_attendance,
    create_event, get_user_by_tg_id, get_event_by_id,
    is_user_president, is_user_admin
)
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
    waiting_for_event_date = State()
    waiting_for_location = State()


async def check_admin(user_id: int, allowed_roles: list = None, club_id_needed: int = None):
    """
    Check if user has admin privileges.
    Uses shared users table: SUPER_ADMIN_ID -> SUPER_ADMIN, is_cp=1 -> PRESIDENT.
    Returns True/False.
    """
    if await is_user_admin(user_id):
        return True

    if allowed_roles and 'SUPER_ADMIN' in allowed_roles and len(allowed_roles) == 1:
        # Only SUPER_ADMIN allowed
        return False

    # Check if president
    is_pres = await is_user_president(user_id)
    if not is_pres:
        return False

    # If club check needed
    if club_id_needed is not None:
        user = await get_user_by_tg_id(user_id)
        if not user or user.get('club_id') != club_id_needed:
            return False

    return True


@admin_router.message(F.text == "Super Admin Panel")
async def super_admin_panel(message: Message):
    if not await is_user_admin(message.from_user.id):
        return
    text = (
        "<b>SUPER ADMIN PANEL</b>\n\n"
        "Quyidagi komandalardan foydalaning:\n"
        "Tadbirlarni boshqarish uchun 'Klub Boshqaruvi' tugmasini bosing."
    )
    await message.answer(text, parse_mode="HTML")


@admin_router.message(F.text == "Klub Boshqaruvi")
async def show_admin_panel(message: Message):
    user = await get_user_by_tg_id(message.from_user.id)
    if not user:
        return await message.answer("Siz tizimda ro'yxatdan o'tmagansiz.")

    is_admin = await is_user_admin(message.from_user.id)
    is_president = await is_user_president(message.from_user.id)

    if not is_admin and not is_president:
        return await message.answer("Sizda bu funksiya uchun ruxsat yo'q. Faqat klub prezidentlari va adminlar foydalanishi mumkin.")

    events = await get_active_events(limit=20)

    # FIX 3: If president (not super admin), only show their club's events
    if is_president and not is_admin:
        events = [e for e in events if e.club_id == user.get('club_id')]

    if not events:
        await message.answer(
            "Hozircha ochiq tadbirlar yo'q. Yangi tadbir yaratishingiz mumkin:",
            reply_markup=admin_events_keyboard([])
        )
    else:
        await message.answer(
            "Boshqarish uchun tadbirni tanlang:",
            reply_markup=admin_events_keyboard(events)
        )


@admin_router.callback_query(F.data.startswith("manage_event_"))
async def manage_specific_event(call: CallbackQuery):
    await call.answer()

    parts = call.data.split("_")
    if len(parts) < 3:
        return await call.message.answer("Noto'g'ri ma'lumot")

    try:
        event_id = int(parts[2])
    except (ValueError, IndexError):
        return await call.message.answer("Tadbir ID noto'g'ri")

    event = await get_event_by_id(event_id)
    if not event:
        return await call.message.answer("Tadbir topilmadi")

    if not await check_admin(call.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN'], event.club_id):
        return await call.message.answer("Siz bu tadbirga mas'ul emassiz!")

    registrations = await get_event_registrations(event_id)
    if not registrations:
        return await call.message.answer("Bu tadbirga hali hech kim ro'yxatdan o'tmagan.")

    await call.message.answer(f"<b>Davomat (Event ID: {event_id}):</b>", parse_mode="HTML")

    import asyncio
    for i, row in enumerate(registrations):
        reg, user_data = row[0], row[1]
        username_str = html.escape(user_data.get('username', '')) if user_data.get('username') else 'yoq'
        text = f"{html.escape(user_data['full_name'])} (@{username_str})"
        await call.message.answer(text, reply_markup=attendance_keyboard(reg.id, reg.status))
        if (i + 1) % 20 == 0:
            await asyncio.sleep(1)


@admin_router.callback_query(F.data.startswith("att_status_"))
async def att_status_info(call: CallbackQuery):
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

    # Get registration to find event
    from bot.database.db import AsyncSessionLocal
    from sqlalchemy.future import select
    from bot.database.models import Registration

    async with AsyncSessionLocal() as session:
        reg = (await session.execute(select(Registration).where(Registration.id == reg_id))).scalars().first()
        if not reg:
            return await call.answer("Ro'yxatdan o'tish topilmadi", show_alert=True)
        event_id = reg.event_id

    event = await get_event_by_id(event_id)
    if not event:
        return await call.answer("Tadbir topilmadi", show_alert=True)

    if not await check_admin(call.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN'], event.club_id):
        return await call.answer("Ruxsat yo'q", show_alert=True)

    new_status = RegStatus.ATTENDED if action == "yes" else RegStatus.ABSENT
    success = await mark_attendance(reg_id, new_status)

    if success:
        await call.message.edit_reply_markup(reply_markup=attendance_keyboard(reg_id, new_status))
        await call.answer("Saqlandi!")
    else:
        await call.answer("Holat allaqachon shunday o'rnatilgan.", show_alert=False)


@admin_router.callback_query(F.data == "add_new_event")
async def add_event_start(call: CallbackQuery, state: FSMContext):
    if not await check_admin(call.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']):
        return await call.answer("Huquq yo'q", show_alert=True)

    await call.message.answer("1. Yangi tadbir sarlavhasini kiriting (Bekor qilish: /cancel):")
    await state.set_state(EventState.waiting_for_title)
    await call.answer()


@admin_router.message(EventState.waiting_for_title)
async def add_event_title(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']):
        return await state.clear()
    if not message.text:
        return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    await state.update_data(title=message.text)
    await message.answer("2. Tadbir uchun to'liq tavsif (description) yozing:")
    await state.set_state(EventState.waiting_for_desc)


@admin_router.message(EventState.waiting_for_desc)
async def add_event_desc(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']):
        return await state.clear()
    if not message.text:
        return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    await state.update_data(desc=message.text)
    await message.answer("3. Kanalga tashlangan post havolasini (Link) bering (yoki yo'q bo'lsa '-' qoldiring):")
    await state.set_state(EventState.waiting_for_link)


@admin_router.message(EventState.waiting_for_link)
async def add_event_link(message: Message, state: FSMContext):
    if not await check_admin(message.from_user.id, ['VP', 'PRESIDENT', 'SUPER_ADMIN']):
        return await state.clear()
    if not message.text:
        return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi")
    link = None if message.text == "-" else message.text
    await state.update_data(link=link)
    await message.answer("4. Ro'yxatdan o'tish uchun necha ball beriladi? (Raqam yozing, masalan 1):")
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
            return await message.answer("Ball manfiy bo'lishi mumkin emas. Iltimos, musbat son kiriting.")
        await state.update_data(reg_pts=reg_pts)
        await message.answer("5. Qatnashganlik (Davomat) uchun necha ball beriladi? (Masalan 5):")
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
            return await message.answer("Ball manfiy bo'lishi mumkin emas. Iltimos, musbat son kiriting.")

        await state.update_data(att_pts=att_pts)
        await message.answer("6. Tadbir sanasi va vaqtini kiriting:\n   - DD.MM.YYYY HH:MM (masalan: 25.01.2025 14:00)\n   - 'bugun HH:MM' (masalan: bugun 18:00)\n   - 'ertaga HH:MM' (masalan: ertaga 14:00)\n   - '-' sanasiz yaratish (istalgan vaqt skanerlash mumkin)")
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

    from datetime import datetime, timedelta

    event_date = None
    text = message.text.strip().lower()

    if text == '-':
        event_date = None
    elif text.startswith('bugun'):
        # "bugun 18:00" format
        try:
            time_part = text.replace('bugun', '').strip()
            time_obj = datetime.strptime(time_part, "%H:%M")
            now = datetime.utcnow()
            event_date = now.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
        except ValueError:
            return await message.answer("Noto'g'ri format! Masalan: bugun 18:00")
    elif text.startswith('ertaga'):
        # "ertaga 14:00" format
        try:
            time_part = text.replace('ertaga', '').strip()
            time_obj = datetime.strptime(time_part, "%H:%M")
            tomorrow = datetime.utcnow() + timedelta(days=1)
            event_date = tomorrow.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
        except ValueError:
            return await message.answer("Noto'g'ri format! Masalan: ertaga 14:00")
    else:
        try:
            event_date = datetime.strptime(text, "%d.%m.%Y %H:%M")
        except ValueError:
            return await message.answer(
                "Noto'g'ri format! Quyidagilardan birini kiriting:\n"
                "- DD.MM.YYYY HH:MM (masalan: 25.01.2025 14:00)\n"
                "- bugun HH:MM\n"
                "- ertaga HH:MM\n"
                "- '-' o'tkazib yuborish"
            )

    await state.update_data(event_date=event_date)
    await message.answer("7. Tadbir joylashuvini kiriting (yoki '-' o'tkazib yuborish):")
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
    data = await state.get_data()

    success, msg = await create_event(
        title=data['title'],
        desc=data['desc'],
        link=data['link'],
        reg_pts=data['reg_pts'],
        att_pts=data['att_pts'],
        created_by_tg_id=message.from_user.id,
        event_date=data.get('event_date'),
        location=location
    )

    if success:
        await message.answer(f"{msg}")
    else:
        await message.answer(f"Xatolik: {msg}")
    await state.clear()
