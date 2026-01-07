import asyncio
import queue
import threading
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from keyboards import return_gift_menu, return_buttons
from services.back_service import check_back
from utils.monitor_all import message_queue, start_scanner, stop_scanner
from utils.collections_ids import collections_ids
import logging

scanner_thread = None
worker_task = None

logger = logging.getLogger(__name__)

class getGifts(StatesGroup):
    gift_id = State()
    model = State()
    backdrop = State()

router = Router()

async def message_worker(message: Message):
    loop = asyncio.get_running_loop()
    logger.info("Worker Started")

    while True:
        logger.info("waiting queue...")
        try:
            data = await loop.run_in_executor(None, lambda: message_queue.get(timeout=1))
        except queue.Empty:
            continue
        logger.info("got from queue: %s", data)

        await message.answer(
            data["text"],
            reply_markup=return_gift_menu(data["link"]),
            disable_web_page_preview=True,
            parse_mode="HTML",
        )
        logger.info("sent to tg")

async def start_and_check(message: Message, all: bool = True, data: dict = None):
    global scanner_thread, worker_task

    if scanner_thread and scanner_thread.is_alive():
        logger.info("scanner thread already running by user_id: %s | username: %s", message.from_user.id, message.from_user.username)
        await message.answer("Сканер уже запущен")
        return

    if all and data == None:
        logger.info("scanner started with all gifts")
        scanner_thread = threading.Thread(target=start_scanner, args=(True,), daemon=True)
        scanner_thread.start()
    elif not all and data == None:
        logger.info("scanner started with latest gifts")
        scanner_thread = threading.Thread(target=start_scanner, args=(False,), daemon=True)
        scanner_thread.start()
    else:
        logger.info("scanner started with with specific gifts")
        scanner_thread = threading.Thread(target=start_scanner, args=(False, data), daemon=True)
        scanner_thread.start()

    worker_task = asyncio.create_task(message_worker(message))

    await message.answer("Сканер запущен")

@router.message(F.text == "Мониторить все")
async def scan_all(message: Message):
    await start_and_check(message, True)

@router.message(F.text == "Остановить сканер")
async def scan_off(message: Message):
    stop_scanner()

    if worker_task:
        worker_task.cancel()

    await message.answer("Сканер остановлен")

@router.message(F.text == "Мониторить последние")
async def scan_latest(message: Message):
    await start_and_check(message, False)

@router.message(F.text == "Мониторить Определенные")
async def monitor_smth(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(getGifts.gift_id)
    await message.answer(
        "Введите название подарка", reply_markup=return_buttons
    )

@router.message(getGifts.gift_id)
async def get_gift_id(message: Message, state: FSMContext):
    if await check_back(message, state):
        return

    if message.text.strip() not in collections_ids.keys():
        return await message.answer("Введите валидное название подарка")

    gift_id = collections_ids[message.text]

    await state.update_data(gift_id=gift_id)
    await state.set_state(getGifts.model)
    await message.answer("Введите модель подарка или *-* если без")

@router.message(getGifts.model)
async def get_gifts_model(message: Message, state: FSMContext):
    if await check_back(message, state):
        return

    model = message.text
    if model.strip() == "-":
        model = None
    await state.update_data(model=model)

    await state.set_state(getGifts.backdrop)
    await message.answer("Введите задний фон модели *-* если без него")

@router.message(getGifts.backdrop)
async def get_gifts_back(message: Message, state: FSMContext):
    if await check_back(message, state):
        return

    backdrop = message.text
    if backdrop.strip() == "-":
        backdrop = None
    await state.update_data(backdrop=backdrop)
    data = await state.get_data()
    await start_and_check(message, False, data)
    await state.clear()
