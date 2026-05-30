from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from bot.database.models import User, Club, Event, Registration, EventStatus, RegStatus, RoleEnum
from bot.database.db import AsyncSessionLocal
from sqlalchemy import desc

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
            existing.full_name = full_name
            existing.username = username
            if club_id: existing.club_id = club_id
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
        result = await session.execute(select(Club))
        return result.scalars().all()

async def create_club(name: str):
    async with AsyncSessionLocal() as session:
        try:
            new_club = Club(club_name=name)
            session.add(new_club)
            await session.commit()
            await session.refresh(new_club)
            return new_club, "Muvaffaqiyatli yaratildi."
        except IntegrityError:
            await session.rollback()
            return None, "Bunday nomli klub allaqachon mavjud."

# --- EVENT FUNCTIONS ---
async def get_active_events():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event).where(Event.status == EventStatus.ACTIVE).order_by(Event.id.desc()))
        return result.scalars().all()

async def get_event_by_id(event_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event).where(Event.id == event_id))
        return result.scalars().first()

async def create_event(title: str, desc: str, link: str, reg_pts: int, att_pts: int, created_by_tg_id: int):
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == created_by_tg_id))
        user = user_res.scalars().first()
        
        if not user: 
            return False
        
        new_event = Event(
            title=title,
            description=desc,
            post_link=link,
            club_id=user.club_id,
            registration_points=reg_pts,
            attendance_points=att_pts,
            created_by=user.id
        )
        session.add(new_event)
        await session.commit()
        return True

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
            await session.commit()
            return True, f"Muvaffaqiyatli! Sizga {event.registration_points} ball qo'shildi."
        except IntegrityError:
            await session.rollback()
            return False, "Allaqachon ro'yxatdan o'tgansiz!"

async def get_top_users(limit: int = 10):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.role != RoleEnum.SUPER_ADMIN).order_by(desc(User.total_points)).limit(limit)
        )
        return result.scalars().all()

async def get_user_results(user_id: int):
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = user_result.scalars().first()
        if not user: return 0, 0
        
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
        elif status != RegStatus.ATTENDED and reg.status == RegStatus.ATTENDED:
            user.total_points = max(0, user.total_points - event.attendance_points)
            
        reg.status = status
        await session.commit()
        return True

async def promote_user(target_tg_id: int, role_name: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == target_tg_id))
        user = result.scalars().first()
        
        if not user: return False, "Foydalanuvchi topilmadi."
        
        try:
            user.role = RoleEnum[role_name.upper()]
            await session.commit()
            return True, f"{user.full_name} endi {role_name}!"
        except Exception:
            return False, "Noto'g'ri lavozim nomi."
