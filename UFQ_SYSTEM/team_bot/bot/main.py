import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from bot.config import BOT_TOKEN
from bot.database.db import init_db

from bot.handlers.start import start_router
from bot.handlers.admin import admin_router
from bot.handlers.cp import cp_router
from bot.handlers.member import member_router

logging.basicConfig(level=logging.INFO)

async def main():
    if not BOT_TOKEN:
        print("XATOLIK: BOT_TOKEN topilmadi!")
        return

    await init_db()

    redis = Redis(host='localhost', port=6379, db=0)
    storage = RedisStorage(redis=redis)

    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=storage)

    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(cp_router)
    dp.include_router(member_router)

    print("UFQ Jamoa Boti muvaffaqiyatli ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
