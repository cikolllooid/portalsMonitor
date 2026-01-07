from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from keyboards import main_buttons
import logging

router = Router()

logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def start(message: Message):
    text = (
        "👋 Привет!\n\n"
        "Я бот, который следит за новыми NFT-подарками и помогает понять, "
        "какие из них могут быть выгодными.\n\n"
        "Анализирую рынок, историю продаж и активность покупателей.\n\n"
        "Жми кнопки ниже и смотри, что происходит на рынке 👇"
    )
    logger.info("Start command handled | user_id=%s | username=%s",
                message.from_user.id, message.from_user.username)

    await message.answer(text, reply_markup=main_buttons)