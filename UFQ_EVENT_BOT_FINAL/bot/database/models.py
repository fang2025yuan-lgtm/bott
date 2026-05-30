from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Enum, DateTime, UniqueConstraint
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

class Club(Base):
    __tablename__ = 'clubs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    club_name = Column(String, unique=True, nullable=False)
    president_id = Column(Integer, ForeignKey('users.id', use_alter=True), nullable=True)
    vp_id = Column(Integer, ForeignKey('users.id', use_alter=True), nullable=True)
    
    users = relationship("User", back_populates="club", foreign_keys="User.club_id")
    events = relationship("Event", back_populates="club")

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    username = Column(String, nullable=True)
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.USER)
    total_points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    club = relationship("Club", back_populates="users", foreign_keys=[club_id])
    registrations = relationship("Registration", back_populates="user")
    created_events = relationship("Event", back_populates="creator")

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    post_link = Column(String, nullable=True)
    club_id = Column(Integer, ForeignKey('clubs.id'), nullable=True)
    registration_points = Column(Integer, default=1)
    attendance_points = Column(Integer, default=5)
    status = Column(Enum(EventStatus), default=EventStatus.ACTIVE)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)

    club = relationship("Club", back_populates="events")
    creator = relationship("User", back_populates="created_events")
    registrations = relationship("Registration", back_populates="event")

class Registration(Base):
    __tablename__ = 'registrations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    status = Column(Enum(RegStatus), default=RegStatus.REGISTERED)
    reg_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="registrations")
    event = relationship("Event", back_populates="registrations")
    
    __table_args__ = (UniqueConstraint('user_id', 'event_id', name='uq_user_event'),)
