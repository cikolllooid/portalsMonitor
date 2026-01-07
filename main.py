import logging

from aiogram import Bot, Dispatcher
import asyncio
from routers import routers

bot = Bot(token="YOUR BOT TOKEN")
dp = Dispatcher()

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

async def main():
    setup_logging()
    for r in routers:
        dp.include_router(r)

    await dp.start_polling(bot)

asyncio.run(main())