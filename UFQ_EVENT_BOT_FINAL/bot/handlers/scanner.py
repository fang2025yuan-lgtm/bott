from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart, CommandObject
from bot.database.crud import verify_and_checkin, get_user_by_tg_id
import logging

scanner_router = Router()
logger = logging.getLogger(__name__)

@scanner_router.message(CommandStart(deep_link=True))
async def handle_deep_link(message: Message, command: CommandObject):
    """
    Deep link orqali QR skanerlash
    Format: /start chk_E12_U987654321_S7a8b9
    """
    if not command.args:
        return
    
    args = command.args
    
    # Check-in deep link ni qayta ishlash
    if args.startswith("chk_"):
        try:
            # Parametrlarni ajratish
            parts = args.split("_")
            if len(parts) < 4:
                return await message.answer("❌ Noto'g'ri QR kod formati!")
            
            event_id_str = parts[1][1:]  # E12 -> 12
            user_tg_id_str = parts[2][1:]  # U987654321 -> 987654321
            security_hash = parts[3][1:]  # S7a8b9 -> 7a8b9
            
            event_id = int(event_id_str)
            user_tg_id = int(user_tg_id_str)
            
            # Check-in amalga oshirish
            success, msg, user_name = await verify_and_checkin(
                security_hash=security_hash,
                event_id=event_id,
                scanner_tg_id=message.from_user.id
            )
            
            if success:
                await message.answer(
                    f"✅ <b>CHECK-IN MUVAFFAQIYATLI!</b>\n\n{msg}",
                    parse_mode="HTML"
                )
                
                # Foydalanuvchiga xabar yuborish
                try:
                    user = await get_user_by_tg_id(user_tg_id)
                    if user:
                        from bot.main import bot
                        await bot.send_message(
                            user_tg_id,
                            f"🎉 <b>Tabriklaymiz!</b>\n\n{msg}",
                            parse_mode="HTML"
                        )
                except Exception as e:
                    logger.error(f"Foydalanuvchiga xabar yuborishda xatolik: {e}")
            else:
                await message.answer(msg, parse_mode="HTML")
                
        except (ValueError, IndexError) as e:
            logger.error(f"Deep link parsing xatoligi: {e}")
            await message.answer("❌ Noto'g'ri QR kod formati!")
        except Exception as e:
            logger.error(f"Check-in xatoligi: {e}")
            await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

@scanner_router.message(Command("scan"))
async def scan_command(message: Message):
    """
    Skanerlash boshlash komandasi
    """
    user = await get_user_by_tg_id(message.from_user.id)
    
    if not user or user.role.value not in ['VP', 'PRESIDENT', 'SUPER_ADMIN']:
        return await message.answer("❌ Sizda skanerlash huquqi yo'q!")
    
    await message.answer(
        "📱 <b>QR-Kod Skanerlash</b>\n\n"
        "Foydalanuvchining chiptasidagi QR-kodni telefon kamerangiz bilan skanerlang.\n\n"
        "<i>Telefon kamerasini QR-kodga tutganingizda, Telegram avtomatik ravishda havolani ochadi "
        "va bot skanerlashni amalga oshiradi.</i>",
        parse_mode="HTML"
    )

@scanner_router.message(Command("mytickets"))
async def my_tickets_command(message: Message):
    """
    Foydalanuvchining barcha chiptalarini ko'rsatish
    """
    from bot.database.db import AsyncSessionLocal
    from sqlalchemy.future import select
    from sqlalchemy.orm import selectinload
    from bot.database.models import Ticket, Event, User
    
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id).options(selectinload(User.club))
        )
        user = user_result.scalars().first()
        if not user:
            return await message.answer("❌ Foydalanuvchi topilmadi!")
        
        # Foydalanuvchining barcha chiptalarini olish
        tickets_result = await session.execute(
            select(Ticket, Event)
            .join(Event)
            .where(Ticket.user_id == user.id)
            .order_by(Ticket.generated_at.desc())
        )
        tickets = tickets_result.all()
        
        if not tickets:
            return await message.answer("📭 Sizda hali chiptalar yo'q.")
        
        # Har bir chiptani qayta yuborish
        for ticket, event in tickets:
            status_text = "✅ Ishlatilgan" if ticket.is_used else "🎟 Faol"
            used_info = f"\n⏰ Skanerlangan: {ticket.used_at.strftime('%d.%m.%Y %H:%M')}" if ticket.is_used else ""
            
            caption = (
                f"🎟 <b>Chipta</b>\n\n"
                f"📅 <b>Tadbir:</b> {event.title}\n"
                f"📌 <b>PIN:</b> <code>{ticket.ticket_pin}</code>\n"
                f"🔖 <b>Status:</b> {status_text}{used_info}\n\n"
                f"<i>Bu chiptani tadbir kirishida ko'rsating.</i>"
            )
            
            # Chiptani qayta generatsiya qilish (xotirada)
            try:
                from bot.utils.ticket_generator import generate_ticket_image
                
                club_name = user.club.club_name if user.club else "UFQ Community"
                event_date = event.event_date.strftime("%d-%b, %H:%M") if event.event_date else "Tez orada"
                
                ticket_image = await generate_ticket_image(
                    user_full_name=user.full_name,
                    user_points=user.total_points,
                    event_title=event.title,
                    event_date=event_date,
                    club_name=club_name,
                    pin=ticket.ticket_pin,
                    qr_data=ticket.qr_data
                )
                
                from aiogram.types import BufferedInputFile
                photo = BufferedInputFile(ticket_image.read(), filename="ticket.png")
                await message.answer_photo(photo=photo, caption=caption, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Chipta rasmini generatsiya qilishda xatolik: {e}")
                await message.answer(caption, parse_mode="HTML")
