from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from keyboards import main_buttons

async def check_back(message: Message, state: FSMContext):
    if message.text.lower() == "назад":
        await state.clear()
        await message.answer("Возвращаемся в меню", reply_markup=main_buttons)
        return True
    return False
