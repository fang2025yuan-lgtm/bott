from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
from sqlalchemy.pool import NullPool
from bot.database.models import Base
from bot.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Ensure shared tables exist (in case event bot starts before team bot)
    import aiosqlite
    from bot.config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute('''CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            full_name TEXT,
            club_id INTEGER,
            role_id INTEGER,
            is_bp BOOLEAN DEFAULT 0,
            is_cp BOOLEAN DEFAULT 0,
            score INTEGER DEFAULT 0,
            total_points INTEGER DEFAULT 0,
            user_status TEXT DEFAULT 'BRONZE',
            username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
        )''')
        await db.commit()
