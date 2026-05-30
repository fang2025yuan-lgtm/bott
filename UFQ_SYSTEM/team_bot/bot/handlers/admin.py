from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import uuid
import html
from bot.config import ADMIN_ID
from bot.database.db import (get_all_clubs, get_club_members, kick_user, get_all_users, 
                             get_all_cps, create_task, update_club_name, delete_club, 
                             create_club, get_club, get_stats, create_invite)
from bot.keyboards.inline import (clubs_inline_keyboard, clubs_invite_keyboard, members_inline_keyboard, 
                                  target_group_keyboard, club_manage_keyboard)

admin_router = Router()
admin_router.message.filter(F.from_user.id == ADMIN_ID)
admin_router.callback_query.filter(F.from_user.id == ADMIN_ID)

class AdminState(StatesGroup):
    broadcast_msg = State()
    task_title = State()
    task_desc = State()
    add_club = State()
    edit_club = State()

@admin_router.message(F.text == "🧑‍💻 Barcha a'zolar")
async def bp_all_members(message: Message):
    clubs = await get_all_clubs()
    await message.answer("👥 Qaysi klub a'zolarini ko'rmoqchisiz?", reply_markup=clubs_inline_keyboard(clubs, "bp_view"))

@admin_router.callback_query(F.data.startswith("bp_view_"))
async def bp_view_members(call: CallbackQuery):
    club_id = int(call.data.split("_")[2])
    members = await get_club_members(club_id)
    if not members:
        return await call.answer("Bu klubda hozircha a'zolar yo'q.", show_alert=True)
    await call.message.edit_text("👇 O'chirish uchun a'zoni tanlang:", reply_markup=members_inline_keyboard(members, "bp_kick"))
    await call.answer()

@admin_router.callback_query(F.data.startswith("bp_kick_"))
async def bp_kick_member(call: CallbackQuery):
    user_id = int(call.data.split("_")[2])
    await kick_user(user_id)
    await call.answer("A'zo o'chirildi!", show_alert=True)
    await call.message.delete()
    try: await call.bot.send_message(user_id, "⛔ Siz UFQ tizimidan chetlashtirildingiz.")
    except Exception: pass

@admin_router.message(F.text == "📢 Xabar yuborish")
async def bp_broadcast(message: Message, state: FSMContext):
    await message.answer("📢 Xabarni kimlarga yubormoqchisiz?", reply_markup=target_group_keyboard("bp_msg_"))

@admin_router.callback_query(F.data.startswith("bp_msg_tgt_"))
async def bp_msg_target(call: CallbackQuery, state: FSMContext):
    target = call.data.split("_")[3]
    await state.update_data(target=target)
    await call.message.edit_text("✍️ Yuboriladigan xabar matnini kiriting (Bekor qilish: /cancel):")
    await state.set_state(AdminState.broadcast_msg)
    await call.answer()

@admin_router.message(AdminState.broadcast_msg)
async def process_bp_msg(message: Message, state: FSMContext):
    if not message.text: return await message.answer("Iltimos, matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    
    data = await state.get_data()
    target = data.get('target')
    users = await get_all_users() if target == 'all' else await get_all_cps()
    sent = 0
    safe_text = html.escape(message.text)
    for uid in users:
        if uid == ADMIN_ID: continue
        try:
            await message.bot.send_message(uid, f"📢 <b>Bosh Prezidentdan xabar:</b>\n\n{safe_text}", parse_mode="HTML")
            sent += 1
        except Exception: pass
    await message.answer(f"✅ Xabar {sent} ta foydalanuvchiga yuborildi.")
    await state.clear()

@admin_router.message(F.text == "📋 Topshiriq berish")
async def bp_task(message: Message, state: FSMContext):
    await message.answer("🎯 Topshiriqni kimlarga bermoqchisiz?", reply_markup=target_group_keyboard("bp_task_"))

@admin_router.callback_query(F.data.startswith("bp_task_tgt_"))
async def bp_task_target(call: CallbackQuery, state: FSMContext):
    target = call.data.split("_")[3]
    await state.update_data(target=target)
    await call.message.edit_text("✍️ Topshiriq sarlavhasini yozing (Bekor qilish: /cancel):")
    await state.set_state(AdminState.task_title)
    await call.answer()

@admin_router.message(AdminState.task_title)
async def bp_task_title(message: Message, state: FSMContext):
    if not message.text: return await message.answer("Iltimos, matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    await state.update_data(title=message.text)
    await message.answer("📋 Endi to'liq ta'rifni yozing (Bekor qilish: /cancel):")
    await state.set_state(AdminState.task_desc)

@admin_router.message(AdminState.task_desc)
async def bp_task_desc(message: Message, state: FSMContext):
    if not message.text: return await message.answer("Iltimos, matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    
    data = await state.get_data()
    target = data.get('target')
    await create_task(club_id=None, title=data['title'], desc=message.text, created_by_tid=ADMIN_ID, target_group=target)
    
    users = await get_all_users() if target == 'all' else await get_all_cps()
    safe_title = html.escape(data['title'])
    for uid in users:
        if uid == ADMIN_ID: continue
        try: await message.bot.send_message(uid, f"🔔 <b>Yangi Topshiriq (BP):</b> {safe_title}", parse_mode="HTML")
        except Exception: pass
    await message.answer("✅ Topshiriq muvaffaqiyatli saqlandi va hammaga bildirishnoma yuborildi!")
    await state.clear()

@admin_router.message(F.text == "⚙️ Sozlamalar")
async def bp_settings(message: Message):
    await message.answer(f"⚙️ <b>Tizim Sozlamalari</b>\n\n👤 Sizning ID raqamingiz: <code>{message.from_user.id}</code>\n👑 Rol: Bosh Prezident (God Mode)", parse_mode="HTML")

@admin_router.message(F.text == "👥 Jamoa statistikasi")
async def bp_stats(message: Message):
    clubs, users, tasks = await get_stats()
    text = f"📊 <b>Jamoa Statistikasi:</b>\n\n🏢 Jami klublar: {clubs} ta\n👥 Jami a'zolar: {users} ta\n📋 Jami topshiriqlar: {tasks} ta"
    await message.answer(text, parse_mode="HTML")

@admin_router.message(F.text == "🏢 Klublar")
async def show_clubs(message: Message):
    clubs = await get_all_clubs()
    await message.answer("👇 Mavjud klublar ro'yxati (Boshqarish uchun tanlang):", reply_markup=clubs_inline_keyboard(clubs, action="club"))

@admin_router.callback_query(F.data.startswith("club_"))
async def manage_club(call: CallbackQuery):
    club_id = int(call.data.split("_")[1])
    club = await get_club(club_id)
    if club:
        await call.message.edit_text(f"🏢 Klub: <b>{html.escape(club['name'])}</b>\nNima amal bajaramiz?", reply_markup=club_manage_keyboard(club_id), parse_mode="HTML")
    await call.answer()

@admin_router.callback_query(F.data == "back_to_clubs")
async def back_clubs(call: CallbackQuery):
    clubs = await get_all_clubs()
    await call.message.edit_text("👇 Mavjud klublar ro'yxati:", reply_markup=clubs_inline_keyboard(clubs, action="club"))
    await call.answer()

@admin_router.callback_query(F.data.startswith("del_club_"))
async def del_club_cb(call: CallbackQuery):
    club_id = int(call.data.split("_")[2])
    await delete_club(club_id)
    await call.message.edit_text("✅ Klub va uning barcha a'zolari bazadan o'chirildi!")
    await call.answer()

@admin_router.callback_query(F.data.startswith("edit_club_"))
async def edit_club_cb(call: CallbackQuery, state: FSMContext):
    club_id = int(call.data.split("_")[2])
    await state.update_data(club_id=club_id)
    await call.message.answer("✏️ Yangi nomni yozing (Bekor qilish uchun /cancel):")
    await state.set_state(AdminState.edit_club)
    await call.answer()

@admin_router.message(AdminState.edit_club)
async def process_edit_club(message: Message, state: FSMContext):
    if not message.text: return await message.answer("Iltimos, matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    data = await state.get_data()
    await update_club_name(data.get('club_id'), message.text)
    await message.answer(f"✅ Klub nomi o'zgartirildi!")
    await state.clear()

@admin_router.callback_query(F.data == "add_club")
async def add_club_prompt(call: CallbackQuery, state: FSMContext):
    await call.message.answer("➕ Yangi klub nomini kiriting (Bekor qilish uchun /cancel):")
    await state.set_state(AdminState.add_club)
    await call.answer()

@admin_router.message(AdminState.add_club)
async def process_add_club(message: Message, state: FSMContext):
    if not message.text: return await message.answer("Iltimos, matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    await create_club(message.text)
    await message.answer(f"✅ Klub yaratildi!")
    await state.clear()

@admin_router.message(F.text == "👑 Taklifnoma (Invite)")
async def invite_menu(message: Message):
    clubs = await get_all_clubs()
    if not clubs:
        return await message.answer("Avval klub yarating!")
    await message.answer("Qaysi klub uchun CP taklifnomasini yaratmoqchisiz?", reply_markup=clubs_invite_keyboard(clubs))

@admin_router.callback_query(F.data.startswith("invite_club_"))
async def process_invite_generation(call: CallbackQuery):
    club_id = int(call.data.split("_")[2])
    unique_code = str(uuid.uuid4())[:8]
    await create_invite(code=unique_code, target_type='cp', club_id=club_id, created_by=call.from_user.id)
    bot_info = await call.bot.get_me()
    await call.message.edit_text(f"🔗 <b>Yangi CP uchun 1 martalik link yaratildi!</b>\n\n<code>https://t.me/{bot_info.username}?start={unique_code}</code>", parse_mode="HTML")
    await call.answer()
