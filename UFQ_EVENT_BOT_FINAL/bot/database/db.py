from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event, text
from sqlalchemy.pool import NullPool
from bot.database.models import Base
from bot.config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)

# SQLite uchun foreign key larni yoqish
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def _migrate_event_columns(conn):
    """Add missing columns to the events table for upgraded databases."""
    result = await conn.execute(text("PRAGMA table_info(events)"))
    existing_columns = {row[1] for row in result.fetchall()}

    migrations = [
        ("event_date", "ALTER TABLE events ADD COLUMN event_date DATETIME"),
        ("location", "ALTER TABLE events ADD COLUMN location VARCHAR"),
        ("check_in_enabled", "ALTER TABLE events ADD COLUMN check_in_enabled BOOLEAN DEFAULT 0"),
    ]

    for col_name, alter_sql in migrations:
        if col_name not in existing_columns:
            logger.info(f"Adding missing column '{col_name}' to events table")
            await conn.execute(text(alter_sql))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Run migration for existing databases that may lack new columns
        await _migrate_event_columns(conn)
