import aiosqlite
import logging
from contextlib import asynccontextmanager

from bot.config import DB_PATH

logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    try:
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute("PRAGMA foreign_keys=ON")
        db.row_factory = aiosqlite.Row
        yield db
    finally:
        await db.close()


async def init_db():
    async with get_db() as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute('''CREATE TABLE IF NOT EXISTS clubs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY AUTOINCREMENT, club_id INTEGER, name TEXT NOT NULL, is_president BOOLEAN DEFAULT 0, UNIQUE(club_id, name), FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER UNIQUE, full_name TEXT, club_id INTEGER, role_id INTEGER, is_bp BOOLEAN DEFAULT 0, is_cp BOOLEAN DEFAULT 0, score INTEGER DEFAULT 0, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE, FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS invites (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, target_type TEXT NOT NULL, club_id INTEGER, role_id INTEGER, is_used BOOLEAN DEFAULT 0, created_by INTEGER NOT NULL)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, club_id INTEGER NULL, title TEXT, description TEXT, target_group TEXT DEFAULT 'club', target_telegram_id INTEGER, created_by_telegram_id INTEGER, FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS task_submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, telegram_id INTEGER, proof_text TEXT, status TEXT DEFAULT 'pending', submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE, FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE)''')
        await db.commit()

        # Migration: add new columns for event bot integration
        try:
            await db.execute("ALTER TABLE users ADD COLUMN total_points INTEGER DEFAULT 0")
            await db.commit()
        except Exception as e:
            logger.debug(f"Migration total_points: {e}")

        try:
            await db.execute("ALTER TABLE users ADD COLUMN user_status TEXT DEFAULT 'BRONZE'")
            await db.commit()
        except Exception as e:
            logger.debug(f"Migration user_status: {e}")

        try:
            await db.execute("ALTER TABLE users ADD COLUMN username TEXT")
            await db.commit()
        except Exception as e:
            logger.debug(f"Migration username: {e}")

        # Create event bot tables
        await db.execute('''CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            post_link TEXT,
            club_id INTEGER,
            registration_points INTEGER DEFAULT 1,
            attendance_points INTEGER DEFAULT 5,
            status TEXT DEFAULT 'ACTIVE',
            created_by INTEGER NOT NULL,
            event_date TEXT,
            location TEXT,
            check_in_enabled INTEGER DEFAULT 0
        )''')

        await db.execute('''CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            status TEXT DEFAULT 'REGISTERED',
            reg_date TEXT DEFAULT CURRENT_TIMESTAMP,
            check_in_time TEXT,
            UNIQUE(user_id, event_id)
        )''')

        await db.execute('''CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            ticket_pin TEXT NOT NULL UNIQUE,
            security_hash TEXT NOT NULL,
            qr_data TEXT NOT NULL,
            is_used INTEGER DEFAULT 0,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            used_at TEXT,
            UNIQUE(user_id, event_id)
        )''')

        await db.commit()

async def get_stats():
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) as count FROM clubs") as c1: clubs = (await c1.fetchone())['count']
        async with db.execute("SELECT COUNT(*) as count FROM users") as c2: users = (await c2.fetchone())['count']
        async with db.execute("SELECT COUNT(*) as count FROM tasks") as c3: tasks = (await c3.fetchone())['count']
        return clubs, users, tasks

async def get_all_clubs():
    async with get_db() as db:
        async with db.execute("SELECT id, name FROM clubs") as cursor: return await cursor.fetchall()

async def create_club(name: str):
    async with get_db() as db:
        try:
            await db.execute("INSERT INTO clubs (name) VALUES (?)", (name,))
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"create_club error: {e}")
            return False

async def update_club_name(club_id: int, new_name: str):
    async with get_db() as db:
        try:
            await db.execute("UPDATE clubs SET name = ? WHERE id = ?", (new_name, club_id))
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"update_club_name error: {e}")
            return False

async def delete_club(club_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM clubs WHERE id = ?", (club_id,))
        await db.commit()

async def get_club(club_id: int):
    async with get_db() as db:
        async with db.execute("SELECT * FROM clubs WHERE id = ?", (club_id,)) as cursor: return await cursor.fetchone()

async def get_roles(club_id: int):
    async with get_db() as db:
        async with db.execute("SELECT id, name FROM roles WHERE club_id = ?", (club_id,)) as cursor: return await cursor.fetchall()

async def create_role(club_id: int, name: str):
    async with get_db() as db:
        try:
            await db.execute("INSERT INTO roles (club_id, name) VALUES (?, ?)", (club_id, name))
            await db.commit()
            return True
        except aiosqlite.IntegrityError: return False

async def delete_role(role_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        await db.commit()

async def get_club_members(club_id: int):
    async with get_db() as db:
        query = """
            SELECT u.telegram_id, u.full_name, u.is_cp, u.score, r.name as role_name 
            FROM users u 
            LEFT JOIN roles r ON u.role_id = r.id 
            WHERE u.club_id = ? ORDER BY u.is_cp DESC, u.score DESC
        """
        async with db.execute(query, (club_id,)) as cursor: return await cursor.fetchall()

async def get_all_cps():
    async with get_db() as db:
        async with db.execute("SELECT telegram_id FROM users WHERE is_cp = 1") as cursor: 
            return [row['telegram_id'] for row in await cursor.fetchall()]

async def get_all_users():
    async with get_db() as db:
        async with db.execute("SELECT telegram_id FROM users") as cursor: 
            return [row['telegram_id'] for row in await cursor.fetchall()]

async def kick_user(telegram_id: int):
    async with get_db() as db:
        await db.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        await db.commit()

async def get_cp_of_club(club_id: int):
    async with get_db() as db:
        async with db.execute("SELECT telegram_id FROM users WHERE club_id = ? AND is_cp = 1", (club_id,)) as cursor:
            res = await cursor.fetchone()
            return res['telegram_id'] if res else None

async def create_task(club_id: int, title: str, desc: str, created_by_tid: int, target_group: str, target_tid: int = None):
    async with get_db() as db:
        await db.execute("INSERT INTO tasks (club_id, title, description, created_by_telegram_id, target_group, target_telegram_id) VALUES (?, ?, ?, ?, ?, ?)", 
                         (club_id, title, desc, created_by_tid, target_group, target_tid))
        await db.commit()

async def get_member_tasks(telegram_id: int, club_id: int, is_cp: bool):
    query = """
    SELECT t.id, t.title, t.description, ts.status 
    FROM tasks t
    LEFT JOIN task_submissions ts ON t.id = ts.task_id AND ts.telegram_id = ?
    WHERE (ts.status IS NULL OR ts.status = 'rejected')
    AND t.created_by_telegram_id != ?
    AND (
        (t.target_group = 'all') OR
        (t.target_group = 'cps' AND ? = 1) OR
        (t.target_group = 'club' AND t.club_id = ?) OR
        (t.target_group = 'individual' AND t.target_telegram_id = ?)
    ) ORDER BY t.id DESC LIMIT 15
    """
    async with get_db() as db:
        async with db.execute(query, (telegram_id, telegram_id, 1 if is_cp else 0, club_id, telegram_id)) as cursor: 
            return await cursor.fetchall()

async def get_task(task_id: int):
    async with get_db() as db:
        async with db.execute("SELECT id, title, description, created_by_telegram_id FROM tasks WHERE id = ?", (task_id,)) as cursor: 
            return await cursor.fetchone()

async def get_cp_created_tasks(created_by_tid: int):
    async with get_db() as db:
        async with db.execute("SELECT id, title FROM tasks WHERE created_by_telegram_id = ? ORDER BY id DESC LIMIT 50", (created_by_tid,)) as cursor: 
            return await cursor.fetchall()

async def submit_task(task_id: int, telegram_id: int, proof: str):
    async with get_db() as db:
        async with db.execute("SELECT id FROM task_submissions WHERE task_id=? AND telegram_id=? AND status IN ('pending', 'approved')", (task_id, telegram_id)) as cursor:
            if await cursor.fetchone(): return -1
        await db.execute("INSERT INTO task_submissions (task_id, telegram_id, proof_text) VALUES (?, ?, ?)", (task_id, telegram_id, proof))
        await db.commit()
        async with db.execute("SELECT last_insert_rowid() as sub_id") as cursor: 
            res = await cursor.fetchone()
            return res['sub_id']

async def approve_submission(sub_id: int, telegram_id: int):
    """Approve submission: +10 score, +10 total_points, recalculate user_status."""
    async with get_db() as db:
        cursor = await db.execute("UPDATE task_submissions SET status = 'approved' WHERE id = ? AND status != 'approved'", (sub_id,))
        if cursor.rowcount > 0:
            await db.execute(
                "UPDATE users SET score = score + 10, total_points = total_points + 10 WHERE telegram_id = ?",
                (telegram_id,)
            )
            # Recalculate user_status
            row = await db.execute("SELECT total_points FROM users WHERE telegram_id = ?", (telegram_id,))
            user_row = await row.fetchone()
            if user_row:
                pts = user_row['total_points']
                if pts >= 121:
                    new_status = 'PLATINUM'
                elif pts >= 51:
                    new_status = 'GOLD'
                elif pts >= 16:
                    new_status = 'SILVER'
                else:
                    new_status = 'BRONZE'
                await db.execute(
                    "UPDATE users SET user_status = ? WHERE telegram_id = ?",
                    (new_status, telegram_id)
                )
            await db.commit()
            return True
        return False

async def reject_submission(sub_id: int):
    async with get_db() as db:
        await db.execute("UPDATE task_submissions SET status = 'rejected' WHERE id = ?", (sub_id,)) 
        await db.commit()

async def get_leaderboard(club_id: int):
    async with get_db() as db:
        async with db.execute("SELECT full_name, score FROM users WHERE club_id = ? ORDER BY score DESC LIMIT 10", (club_id,)) as cursor: return await cursor.fetchall()

async def get_user(telegram_id: int):
    async with get_db() as db:
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor: return await cursor.fetchone()

async def get_user_full(telegram_id: int):
    async with get_db() as db:
        query = "SELECT u.*, r.name as role_name FROM users u LEFT JOIN roles r ON u.role_id = r.id WHERE u.telegram_id = ?"
        async with db.execute(query, (telegram_id,)) as cursor: return await cursor.fetchone()

async def create_invite(code: str, target_type: str, club_id: int, created_by: int, role_id: int = None):
    async with get_db() as db:
        await db.execute("INSERT INTO invites (code, target_type, club_id, role_id, created_by) VALUES (?, ?, ?, ?, ?)", (code, target_type, club_id, role_id, created_by))
        await db.commit()

async def get_invite(code: str):
    async with get_db() as db:
        async with db.execute("SELECT * FROM invites WHERE code = ? AND is_used = 0", (code,)) as cursor: return await cursor.fetchone()

async def use_invite(code: str):
    async with get_db() as db:
        await db.execute("UPDATE invites SET is_used = 1 WHERE code = ?", (code,))
        await db.commit()

async def use_invite_atomic(code: str):
    """Atomically mark invite as used and return its data. Returns None if already used."""
    async with get_db() as db:
        # First get the invite data
        async with db.execute("SELECT * FROM invites WHERE code = ? AND is_used = 0", (code,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        # Atomically mark as used (only succeeds if still is_used=0)
        update_cursor = await db.execute(
            "UPDATE invites SET is_used = 1 WHERE code = ? AND is_used = 0", (code,)
        )
        if update_cursor.rowcount > 0:
            await db.commit()
            return row
        return None

async def create_user(telegram_id: int, full_name: str, club_id: int, role_id: int, is_cp: bool):
    async with get_db() as db:
        query = """
        INSERT INTO users (telegram_id, full_name, club_id, role_id, is_cp) 
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET 
            full_name=excluded.full_name,
            club_id=excluded.club_id,
            role_id=excluded.role_id,
            is_cp=excluded.is_cp
        """
        await db.execute(query, (telegram_id, full_name, club_id, role_id, is_cp))
        await db.commit()
