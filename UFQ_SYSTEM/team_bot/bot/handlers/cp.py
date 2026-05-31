from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import uuid
import html
import logging

from bot.database.db import (get_user, create_role, get_roles, create_task, create_invite, 
                             get_club_members, get_cp_created_tasks, approve_submission, 
                             reject_submission, delete_role)
from bot.keyboards.inline import (cp_roles_keyboard, roles_invite_keyboard, members_inline_keyboard, 
                                  target_cp_group_keyboard, role_manage_keyboard)

cp_router = Router()
logger = logging.getLogger(__name__)

class CPState(StatesGroup):
    add_role = State()
    broadcast = State()
    task_title = State()
    task_desc = State()

@cp_router.message(F.text == "🎭 Lavozimlar")
async def cp_roles(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return
    roles = await get_roles(user['club_id'])
    await message.answer("Sizning klubingizdagi lavozimlar:", reply_markup=cp_roles_keyboard(roles))

@cp_router.callback_query(F.data.startswith("role_"))
async def role_info(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user or not user['is_cp']: return await call.answer("Xuxuq yo'q", show_alert=True)
    role_id = int(call.data.split("_")[1])
    await call.message.edit_text("Ushbu lavozimni nima qilamiz?", reply_markup=role_manage_keyboard(role_id))
    await call.answer()

@cp_router.callback_query(F.data == "back_to_roles")
async def back_to_roles(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user or not user['is_cp']: return await call.answer("Xuxuq yo'q", show_alert=True)
    roles = await get_roles(user['club_id'])
    await call.message.edit_text("Sizning klubingizdagi lavozimlar:", reply_markup=cp_roles_keyboard(roles))
    await call.answer()

@cp_router.callback_query(F.data.startswith("del_role_"))
async def del_role_cb(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user or not user['is_cp']: return await call.answer("Xuxuq yo'q", show_alert=True)
    role_id = int(call.data.split("_")[2])
    await delete_role(role_id)
    await call.message.edit_text("✅ Lavozim o'chirildi.")
    await call.answer()

@cp_router.callback_query(F.data == "add_role")
async def cp_add_role(call: CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    if not user or not user['is_cp']: return await call.answer("Xuxuq yo'q", show_alert=True)
    await call.message.answer("Yangi lavozim nomini yozing (Masalan: Mentor). Bekor qilish: /cancel")
    await state.set_state(CPState.add_role)
    await call.answer()

@cp_router.message(CPState.add_role)
async def process_add_role(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    
    success = await create_role(user['club_id'], message.text)
    if success:
        await message.answer(f"✅ Lavozim '{message.text}' qo'shildi!")
    else:
        await message.answer(f"⚠️ Bu nomdagi lavozim allaqachon mavjud.")
    await state.clear()

@cp_router.message(F.text == "🤝 Jamoa yig'ish")
async def cp_invite(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return
    roles = await get_roles(user['club_id'])
    await message.answer("Taklifnoma qaysi lavozim uchun yaratilsin?", reply_markup=roles_invite_keyboard(roles))

@cp_router.callback_query(F.data.startswith("invite_role_"))
async def process_role_invite(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user or not user['is_cp']: return await call.answer("Sizda ruxsat yo'q!", show_alert=True)
    role_id = int(call.data.split("_")[2])
    role_id = role_id if role_id > 0 else None
    unique_code = str(uuid.uuid4())[:8]
    await create_invite(code=unique_code, target_type='member', club_id=user['club_id'], created_by=call.from_user.id, role_id=role_id)
    bot_info = await call.bot.get_me()
    await call.message.edit_text(f"🔗 <b>Yangi a'zo uchun link:</b>\n\n<code>https://t.me/{bot_info.username}?start={unique_code}</code>\n\n<i>Bu link faqat 1 marta ishlaydi!</i>", parse_mode="HTML")
    await call.answer()

@cp_router.message(F.text == "👥 Mening Jamoam")
async def cp_team(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return
    members = await get_club_members(user['club_id'])
    if not members: return await message.answer("Jamoangizda hozircha a'zolar yo'q.")
    text = "👥 <b>Jamoa A'zolari:</b>\n\n"
    for idx, m in enumerate(members, 1):
        role_str = m['role_name'] if m['role_name'] else ("Prezident" if m['is_cp'] else "A'zo")
        text += f"{idx}. 👤 {html.escape(m['full_name'])} - <i>{html.escape(role_str)}</i> ({m['score']} ball)\n"
    await message.answer(text, parse_mode="HTML")

@cp_router.message(F.text == "📢 Ommaviy xabar")
async def cp_broadcast(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return
    await message.answer("✍️ Jamoaga yubormoqchi bo'lgan xabaringizni yozing (Bekor qilish: /cancel):")
    await state.set_state(CPState.broadcast)

@cp_router.message(CPState.broadcast)
async def process_cp_broadcast(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    
    members = await get_club_members(user['club_id'])
    sent = 0
    safe_text = html.escape(message.text)
    for m in members:
        if m['telegram_id'] == user['telegram_id']: continue
        try:
            await message.bot.send_message(m['telegram_id'], f"📢 <b>Prezidentdan xabar:</b>\n\n{safe_text}", parse_mode="HTML")
            sent += 1
        except Exception as e: logger.error(f"Broadcast xabari yuborishda xatolik ({m['telegram_id']}): {e}")
    await message.answer(f"✅ Xabar {sent} ta a'zoga yuborildi.")
    await state.clear()

@cp_router.message(F.text == "📤 Bergan topshiriqlarim")
async def cp_my_tasks(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return
    tasks = await get_cp_created_tasks(user['telegram_id'])
    if not tasks: return await message.answer("Siz hali topshiriq bermagansiz.")
    text = "📤 <b>Siz yaratgan topshiriqlar:</b>\n\n"
    for t in tasks: text += f"- {html.escape(t['title'])} (ID: {t['id']})\n"
    await message.answer(text, parse_mode="HTML")

@cp_router.message(F.text == "📋 Topshiriq berish")
async def cp_task(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return
    await message.answer("🎯 Topshiriqni kimlarga bermoqchisiz?", reply_markup=target_cp_group_keyboard())

@cp_router.callback_query(F.data.startswith("cp_tgt_"))
async def cp_task_tgt(call: CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    if not user or not user['is_cp']: return await call.answer("Xuxuq yo'q", show_alert=True)
    tgt = call.data.split("_")[2]
    if tgt == "ind":
        members = await get_club_members(user['club_id'])
        if not members: return await call.answer("A'zolar yo'q", show_alert=True)
        await call.message.edit_text("👇 Qaysi a'zoga topshiriq bermoqchisiz?", reply_markup=members_inline_keyboard(members, "cptask_ind"))
    else:
        await state.update_data(target='club', tgt_id=None)
        await call.message.edit_text("✍️ Topshiriq sarlavhasini yozing (Bekor qilish: /cancel):")
        await state.set_state(CPState.task_title)
    await call.answer()

@cp_router.callback_query(F.data.startswith("cptask_ind_"))
async def cp_task_ind(call: CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    if not user or not user['is_cp']: return await call.answer("Xuxuq yo'q", show_alert=True)
    target_id = int(call.data.split("_")[2])
    await state.update_data(target='individual', tgt_id=target_id)
    await call.message.edit_text("✍️ Topshiriq sarlavhasini yozing (Bekor qilish: /cancel):")
    await state.set_state(CPState.task_title)
    await call.answer()

@cp_router.message(CPState.task_title)
async def cp_task_title(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    await state.update_data(title=message.text)
    await message.answer("📋 Endi to'liq ta'rifni yozing (Bekor qilish: /cancel):")
    await state.set_state(CPState.task_desc)

@cp_router.message(CPState.task_desc)
async def cp_task_desc(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user or not user['is_cp']: return await state.clear()
    if not message.text: return await message.answer("Matn yuboring (/cancel)")
    if message.text == '/cancel':
        await state.clear()
        return await message.answer("Bekor qilindi.")
    
    data = await state.get_data()
    target, tgt_id = data.get('target'), data.get('tgt_id')
    
    await create_task(user['club_id'], data['title'], message.text, user['telegram_id'], target, tgt_id)
    
    safe_title = html.escape(data['title'])
    if target == 'club':
        members = await get_club_members(user['club_id'])
        for m in members:
            if m['telegram_id'] == user['telegram_id']: continue
            try: await message.bot.send_message(m['telegram_id'], f"🔔 <b>Yangi Topshiriq:</b> {safe_title}", parse_mode="HTML")
            except Exception as e: logger.error(f"Topshiriq bildirishnomasi xatolik ({m['telegram_id']}): {e}")
    else:
        try: await message.bot.send_message(tgt_id, f"🔔 <b>Sizga Shaxsiy Topshiriq:</b> {safe_title}", parse_mode="HTML")
        except Exception as e: logger.error(f"Shaxsiy topshiriq bildirishnomasi xatolik ({tgt_id}): {e}")

    await message.answer("✅ Topshiriq saqlandi va bildirishnoma yuborildi!")
    await state.clear()

from bot.config import ADMIN_ID
@cp_router.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_"))
async def review_sub(call: CallbackQuery):
    is_admin = (call.from_user.id == ADMIN_ID)
    user = await get_user(call.from_user.id)
    
    if not is_admin and (not user or not user['is_cp']):
        return await call.answer("Xuxuq yo'q", show_alert=True)
    
    action, sub_id, telegram_id = call.data.split("_")
    sub_id, telegram_id = int(sub_id), int(telegram_id)
    
    if action == "approve":
        success = await approve_submission(sub_id, telegram_id)
        if success:
            await call.message.edit_text(call.message.text + "\n\n✅ <b>Qabul qilindi va 10 ball berildi!</b>", parse_mode="HTML")
            try: await call.bot.send_message(telegram_id, "🎉 Topshirig'ingiz Prezident tomonidan QABUL QILINDI! (+10 ball)")
            except Exception as e: logger.error(f"Tasdiqlash xabari yuborishda xatolik ({telegram_id}): {e}")
        else:
            await call.answer("Allaqachon tekshirilgan!", show_alert=True)
    else:
        await reject_submission(sub_id)
        await call.message.edit_text(call.message.text + "\n\n❌ <b>Rad etildi!</b>", parse_mode="HTML")
        try: await call.bot.send_message(telegram_id, "⚠️ Topshirig'ingiz Rad Etildi. Qayta urinib ko'ring (Mening Topshiriqlarim qismidan).")
        except Exception as e: logger.error(f"Rad etish xabari yuborishda xatolik ({telegram_id}): {e}")
    await call.answer()
