from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from bot.database.models import User, Club, Event, Registration, Ticket, EventStatus, RegStatus, RoleEnum, UserStatus
from bot.database.db import AsyncSessionLocal
from bot.utils.ticket_generator import generate_pin, generate_security_hash, generate_qr_data, generate_ticket_image
from bot.utils.status_manager import calculate_user_status
from sqlalchemy import desc
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# --- USER FUNCTIONS ---
async def get_user_by_tg_id(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalars().first()

async def create_user(telegram_id: int, full_name: str, username: str = None, club_id: int = None, role: RoleEnum = RoleEnum.USER):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        existing = result.scalars().first()
        if existing:
            # Foydalanuvchi mavjud bo'lsa, faqat username ni yangilash
            # full_name va club_id ni o'zgartirmaslik (birinchi ro'yxatdan o'tish ma'lumotlarini saqlash)
            if username:
                existing.username = username
            await session.commit()
            await session.refresh(existing)
            return existing
        
        new_user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            club_id=club_id,
            role=role
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user

async def update_user_role(telegram_id: int, role: RoleEnum):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalars().first()
        if user:
            user.role = role
            await session.commit()
            return True
        return False

# --- CLUB FUNCTIONS ---
async def get_all_clubs():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Club).options(selectinload(Club.users)))
        return result.scalars().all()

async def create_club(name: str, president_tg_id: int = None):
    async with AsyncSessionLocal() as session:
        try:
            new_club = Club(club_name=name)
            session.add(new_club)
            await session.flush()

            if president_tg_id:
                user_result = await session.execute(
                    select(User).where(User.telegram_id == president_tg_id)
                )
                user = user_result.scalars().first()
                if user:
                    user.role = RoleEnum.PRESIDENT
                    user.club_id = new_club.id
                    new_club.president_id = user.id

            await session.commit()
            await session.refresh(new_club)
            return new_club, "Muvaffaqiyatli yaratildi."
        except IntegrityError:
            await session.rollback()
            return None, "Bunday nomli klub allaqachon mavjud."

# --- EVENT FUNCTIONS ---
async def get_active_events(limit: int = 50):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Event).where(Event.status == EventStatus.ACTIVE).order_by(Event.id.desc()).limit(limit)
        )
        return result.scalars().all()

async def get_event_by_id(event_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event).where(Event.id == event_id))
        return result.scalars().first()

async def get_events_by_club(club_id: int):
    """Klub bo'yicha ACTIVE tadbirlarni olish"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Event).where(
                Event.club_id == club_id,
                Event.status == EventStatus.ACTIVE
            ).order_by(Event.id.desc())
        )
        return result.scalars().all()

ALLOWED_EVENT_FIELDS = {
    'title', 'description', 'post_link', 'registration_points',
    'attendance_points', 'status', 'event_date', 'location', 'check_in_enabled'
}

async def update_event_field(event_id: int, field_name: str, value):
    """Tadbir maydonini alohida yangilash"""
    if field_name not in ALLOWED_EVENT_FIELDS:
        return False, "Noto'g'ri maydon nomi"
    async with AsyncSessionLocal() as session:
        event = await session.get(Event, event_id)
        if not event:
            return False, "Tadbir topilmadi"
        setattr(event, field_name, value)
        await session.commit()
        return True, "Tadbir yangilandi"

async def create_event(title: str, desc: str, link: str, reg_pts: int, att_pts: int, created_by_tg_id: int, event_date=None, location=None, check_in_enabled=False, club_id_override: int = None):
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == created_by_tg_id))
        user = user_res.scalars().first()
        
        if not user: 
            return False, "Foydalanuvchi topilmadi"
        
        club_id = club_id_override if club_id_override is not None else user.club_id
        
        new_event = Event(
            title=title,
            description=desc,
            post_link=link,
            club_id=club_id,
            registration_points=reg_pts,
            attendance_points=att_pts,
            created_by=user.id,
            event_date=event_date,
            location=location,
            check_in_enabled=check_in_enabled
        )
        session.add(new_event)
        await session.commit()
        return True, "Muvaffaqiyatli yaratildi"

# --- REGISTRATION & LEADERBOARD FUNCTIONS ---
async def register_user_for_event(user_tg_id: int, event_id: int):
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == user_tg_id))
        user = user_result.scalars().first()
        if not user: return False, "Foydalanuvchi topilmadi"

        event = await session.get(Event, event_id)
        if not event or event.status != EventStatus.ACTIVE:
            return False, "Tadbir topilmadi yoki yopilgan."

        try:
            new_reg = Registration(user_id=user.id, event_id=event_id)
            session.add(new_reg)
            user.total_points += event.registration_points
            user.user_status = calculate_user_status(user.total_points)
            await session.commit()
            return True, f"Muvaffaqiyatli! Sizga {event.registration_points} ball qo'shildi."
        except IntegrityError:
            await session.rollback()
            return False, "Allaqachon ro'yxatdan o'tgansiz!"

async def get_top_users(limit: int = 10):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                User.role != RoleEnum.SUPER_ADMIN  # SUPER_ADMIN dan boshqa hamma
            ).order_by(desc(User.total_points)).limit(limit)
        )
        return result.scalars().all()

async def get_user_results(telegram_id: int):
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user_result.scalars().first()
        if not user: 
            return 0, 0
        
        regs_result = await session.execute(
            select(Registration).where(Registration.user_id == user.id, Registration.status == RegStatus.ATTENDED)
        )
        attended_events = len(regs_result.scalars().all())
        return user.total_points, attended_events

async def get_event_registrations(event_id: int):
    async with AsyncSessionLocal() as session:
        query = select(Registration, User).join(User).where(Registration.event_id == event_id)
        result = await session.execute(query)
        return result.all()

async def mark_attendance(reg_id: int, status: RegStatus):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Registration).where(Registration.id == reg_id))
        reg = result.scalars().first()
        
        if not reg: 
            return False
        if reg.status == status: 
            return False 
        
        event = await session.get(Event, reg.event_id)
        user = await session.get(User, reg.user_id)
        
        if not event or not user: 
            return False

        if status == RegStatus.ATTENDED and reg.status != RegStatus.ATTENDED:
            user.total_points += event.attendance_points
            # Chiptani ishlatilgan deb belgilash
            ticket_result = await session.execute(
                select(Ticket).where(
                    Ticket.user_id == user.id,
                    Ticket.event_id == reg.event_id
                )
            )
            ticket = ticket_result.scalars().first()
            if ticket:
                ticket.is_used = True
                ticket.used_at = datetime.utcnow()
        elif status != RegStatus.ATTENDED and reg.status == RegStatus.ATTENDED:
            user.total_points = max(0, user.total_points - event.attendance_points)
            # Chiptani qaytarish
            ticket_result = await session.execute(
                select(Ticket).where(
                    Ticket.user_id == user.id,
                    Ticket.event_id == reg.event_id
                )
            )
            ticket = ticket_result.scalars().first()
            if ticket:
                ticket.is_used = False
                ticket.used_at = None
            
        reg.status = status
        user.user_status = calculate_user_status(user.total_points)
        await session.commit()
        return True

async def promote_user(target_tg_id: int, role_name: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == target_tg_id))
        user = result.scalars().first()
        
        if not user: 
            return False, "Foydalanuvchi topilmadi."
        
        # SUPER_ADMIN ga ko'tarish taqiqlangan
        if role_name.upper() == 'SUPER_ADMIN':
            return False, "SUPER_ADMIN rolini faqat tizim berishi mumkin."
        
        try:
            new_role = RoleEnum[role_name.upper()]
            user.role = new_role
            
            # Agar PRESIDENT yoki VP berilsa, club jadvalini yangilash
            if user.club_id and new_role in [RoleEnum.PRESIDENT, RoleEnum.VP]:
                club_result = await session.execute(select(Club).where(Club.id == user.club_id))
                club = club_result.scalars().first()
                if club:
                    if new_role == RoleEnum.PRESIDENT:
                        club.president_id = user.id
                    elif new_role == RoleEnum.VP:
                        club.vp_id = user.id
            
            await session.commit()
            return True, f"{user.full_name} endi {role_name}!"
        except KeyError:
            return False, "Noto'g'ri lavozim nomi."



# --- TICKET FUNCTIONS ---
async def create_ticket(user_tg_id: int, event_id: int):
    """
    Foydalanuvchi uchun chipta yaratish
    Returns: (Ticket object, BytesIO rasm) yoki (None, error_message)
    """
    async with AsyncSessionLocal() as session:
        # Foydalanuvchini topish
        user_result = await session.execute(
            select(User).where(User.telegram_id == user_tg_id).options(selectinload(User.club))
        )
        user = user_result.scalars().first()
        if not user:
            return None, "Foydalanuvchi topilmadi"
        
        # Eventni topish
        event = await session.get(Event, event_id)
        if not event:
            return None, "Tadbir topilmadi"
        
        # Allaqachon chipta bormi tekshirish
        existing = await session.execute(
            select(Ticket).where(Ticket.user_id == user.id, Ticket.event_id == event_id)
        )
        if existing.scalars().first():
            return None, "Allaqachon chipta mavjud"
        
        # Save user data before retry loop to avoid expired object issues after rollback
        saved_user_id = user.id
        saved_user_full_name = user.full_name
        saved_user_total_points = user.total_points
        saved_user_telegram_id = user.telegram_id
        saved_club_name = user.club.club_name if user.club else "UFQ Community"
        saved_event_title = event.title
        saved_event_date = event.event_date
        
        # PIN va xavfsizlik hash generatsiya (retry loop for PIN collision)
        max_attempts = 5
        for attempt in range(max_attempts):
            pin = generate_pin()
            security_hash = generate_security_hash(saved_user_id, event_id, pin)
            qr_data = generate_qr_data(event_id, saved_user_telegram_id, security_hash)
            
            # Ticket yaratish
            ticket = Ticket(
                user_id=saved_user_id,
                event_id=event_id,
                ticket_pin=pin,
                security_hash=security_hash,
                qr_data=qr_data
            )
            session.add(ticket)
            try:
                await session.flush()
                break
            except IntegrityError:
                await session.rollback()
                if attempt == max_attempts - 1:
                    return None, "PIN generatsiya qilishda xatolik. Qaytadan urinib ko'ring."
                continue
        
        await session.commit()
        await session.refresh(ticket)
        
        # Chipta rasmini generatsiya qilish (using saved data to avoid detached instance issues)
        event_date_str = saved_event_date.strftime("%d-%b, %H:%M") if saved_event_date else "Tez orada"
        
        ticket_image = await generate_ticket_image(
            user_full_name=saved_user_full_name,
            user_points=saved_user_total_points,
            event_title=saved_event_title,
            event_date=event_date_str,
            club_name=saved_club_name,
            pin=pin,
            qr_data=qr_data
        )
        
        return ticket, ticket_image

async def verify_and_checkin(security_hash: str, event_id: int, scanner_tg_id: int):
    """
    QR kod skanerlash va check-in amalga oshirish
    Returns: (success: bool, message: str, user_name: str or None, user_telegram_id: int or None)
    """
    async with AsyncSessionLocal() as session:
        # Scanner vakolatini tekshirish
        scanner_result = await session.execute(select(User).where(User.telegram_id == scanner_tg_id))
        scanner = scanner_result.scalars().first()
        
        if not scanner or scanner.role not in [RoleEnum.VP, RoleEnum.PRESIDENT, RoleEnum.SUPER_ADMIN]:
            return False, "❌ Sizda skanerlash huquqi yo'q!", None, None
        
        # Chiptani topish
        ticket_result = await session.execute(
            select(Ticket).where(
                Ticket.security_hash == security_hash,
                Ticket.event_id == event_id
            )
        )
        ticket = ticket_result.scalars().first()
        
        if not ticket:
            return False, "❌ Noto'g'ri yoki yaroqsiz chipta!", None, None
        
        # Allaqachon ishlatilganmi?
        if ticket.is_used:
            used_time = ticket.used_at.strftime("%H:%M") if ticket.used_at else "noma'lum vaqt"
            return False, f"⚠️ Bu chipta allaqachon ishlatilgan!\nSkanerlangan vaqt: {used_time}", None, None
        
        # Eventni va foydalanuvchini olish
        event = await session.get(Event, event_id)
        user = await session.get(User, ticket.user_id)
        
        if not event or not user:
            return False, "❌ Xatolik: Ma'lumot topilmadi", None, None
        
        # Check-in yoqilganmi tekshirish
        if not event.check_in_enabled:
            return False, "❌ QR skanerlash bu tadbir uchun yoqilmagan!", None, None
        
        # Scanner ushbu klubning admin bo'lishi kerak
        if scanner.role != RoleEnum.SUPER_ADMIN:
            if not event.club_id or scanner.club_id != event.club_id:
                return False, "❌ Siz bu tadbirni boshqara olmaysiz!", None, None
        
        # Registration ni yangilash
        reg_result = await session.execute(
            select(Registration).where(
                Registration.user_id == user.id,
                Registration.event_id == event_id
            )
        )
        registration = reg_result.scalars().first()
        
        if not registration:
            return False, "❌ Foydalanuvchi bu tadbirga ro'yxatdan o'tmagan!", None, None
        
        # Allaqachon tashrif buyurganmi tekshirish
        if registration.status == RegStatus.ATTENDED:
            return False, "⚠️ Bu foydalanuvchi allaqachon tashrif buyurgan!", None, None
        
        # Check-in amalga oshirish
        ticket.is_used = True
        ticket.used_at = datetime.utcnow()
        registration.status = RegStatus.ATTENDED
        registration.check_in_time = datetime.utcnow()
        
        # Ball qo'shish
        old_points = user.total_points
        user.total_points += event.attendance_points
        
        # Statusni yangilash
        new_status = calculate_user_status(user.total_points)
        old_status = user.user_status
        user.user_status = new_status
        
        await session.commit()
        
        # Status o'zgargan bo'lsa, maxsus xabar
        status_change_msg = ""
        if old_status != new_status:
            from bot.utils.status_manager import get_status_name_uz
            status_change_msg = f"\n🎊 Tabriklaymiz! Sizning statusingiz o'zgarti: {get_status_name_uz(old_status)} → {get_status_name_uz(new_status)}"
        
        success_msg = f"✅ Muvaffaqiyatli!\n\n👤 {user.full_name}\n📅 {event.title}\n🎁 +{event.attendance_points} ball qo'shildi (Jami: {user.total_points}){status_change_msg}"
        
        return True, success_msg, user.full_name, user.telegram_id

async def update_user_status_if_needed(user_id: int):
    """Foydalanuvchi statusini yangilash (ball o'zgarsa)"""
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            return
        
        new_status = calculate_user_status(user.total_points)
        if user.user_status != new_status:
            user.user_status = new_status
            await session.commit()


# --- SUPER ADMIN CRUD FUNCTIONS ---

async def get_all_users(limit: int = 20, offset: int = 0):
    """Barcha foydalanuvchilarni sahifalab olish"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).order_by(desc(User.total_points)).limit(limit).offset(offset)
        )
        return result.scalars().all()


async def get_all_events(limit: int = 20, offset: int = 0):
    """Barcha tadbirlarni sahifalab olish (holati bo'yicha filter yo'q)"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Event).order_by(desc(Event.id)).limit(limit).offset(offset)
        )
        return result.scalars().all()


async def update_event(event_id: int, **kwargs):
    """Tadbir maydonlarini yangilash"""
    async with AsyncSessionLocal() as session:
        event = await session.get(Event, event_id)
        if not event:
            return False, "Tadbir topilmadi"
        for key, value in kwargs.items():
            if key not in ALLOWED_EVENT_FIELDS:
                continue
            setattr(event, key, value)
        await session.commit()
        return True, "Tadbir yangilandi"


async def cancel_event(event_id: int):
    """Tadbirni bekor qilish (CANCELLED holatiga o'tkazish)"""
    async with AsyncSessionLocal() as session:
        event = await session.get(Event, event_id)
        if not event:
            return False, "Tadbir topilmadi"
        event.status = EventStatus.CANCELLED
        await session.commit()
        return True, "Tadbir bekor qilindi"


async def update_user_club(telegram_id: int, club_id: int):
    """Foydalanuvchining klubini o'zgartirish"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalars().first()
        if not user:
            return False, "Foydalanuvchi topilmadi"
        # Klubni tekshirish
        club = await session.get(Club, club_id)
        if not club:
            return False, "Klub topilmadi"
        user.club_id = club_id
        await session.commit()
        return True, f"Foydalanuvchi '{club.club_name}' klubiga o'tkazildi"


async def update_user_points(telegram_id: int, points: int):
    """Foydalanuvchi ballarini o'rnatish va statusni qayta hisoblash"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalars().first()
        if not user:
            return False, "Foydalanuvchi topilmadi"
        user.total_points = points
        user.user_status = calculate_user_status(points)
        await session.commit()
        return True, f"Ballar {points} ga o'rnatildi. Status: {user.user_status.value}"


async def get_club_by_id(club_id: int):
    """Klubni ID bo'yicha olish"""
    async with AsyncSessionLocal() as session:
        return await session.get(Club, club_id)


async def delete_club(club_id: int):
    """Klubni o'chirish"""
    async with AsyncSessionLocal() as session:
        club = await session.get(Club, club_id)
        if not club:
            return False, "Klub topilmadi"
        await session.delete(club)
        await session.commit()
        return True, f"'{club.club_name}' klubi o'chirildi"


async def get_users_count():
    """Jami foydalanuvchilar sonini olish"""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import func
        result = await session.execute(select(func.count(User.id)))
        return result.scalar() or 0


async def get_events_count():
    """Jami tadbirlar sonini olish"""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import func
        result = await session.execute(select(func.count(Event.id)))
        return result.scalar() or 0


async def get_clubs_count():
    """Jami klublar sonini olish"""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import func
        result = await session.execute(select(func.count(Club.id)))
        return result.scalar() or 0
