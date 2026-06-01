from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Enum, DateTime, UniqueConstraint, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()


class RoleEnum(enum.Enum):
    USER = "USER"
    VP = "VP"
    PRESIDENT = "PRESIDENT"
    SUPER_ADMIN = "SUPER_ADMIN"


class EventStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RegStatus(enum.Enum):
    REGISTERED = "REGISTERED"
    ATTENDED = "ATTENDED"
    ABSENT = "ABSENT"


class UserStatus(enum.Enum):
    BRONZE = "BRONZE"      # 0-15 ball
    SILVER = "SILVER"      # 16-50 ball
    GOLD = "GOLD"          # 51-120 ball
    PLATINUM = "PLATINUM"  # 121+ ball


class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    post_link = Column(String, nullable=True)
    club_id = Column(Integer, nullable=True)
    registration_points = Column(Integer, default=1)
    attendance_points = Column(Integer, default=5)
    status = Column(Enum(EventStatus), default=EventStatus.ACTIVE)
    created_by = Column(Integer, nullable=False)
    event_date = Column(DateTime, nullable=True)
    location = Column(String, nullable=True)
    check_in_enabled = Column(Boolean, default=False)


class Registration(Base):
    __tablename__ = 'registrations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    status = Column(Enum(RegStatus), default=RegStatus.REGISTERED)
    reg_date = Column(DateTime, default=datetime.utcnow)
    check_in_time = Column(DateTime, nullable=True)

    event = relationship("Event")

    __table_args__ = (UniqueConstraint('user_id', 'event_id', name='uq_user_event'),)


class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    ticket_pin = Column(String(6), nullable=False, unique=True)
    security_hash = Column(String, nullable=False)
    qr_data = Column(String, nullable=False)
    is_used = Column(Boolean, default=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)

    event = relationship("Event")

    __table_args__ = (UniqueConstraint('user_id', 'event_id', name='uq_ticket_user_event'),)
