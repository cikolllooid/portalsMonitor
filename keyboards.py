from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_buttons = ReplyKeyboardMarkup(
    resize_keyboard=True,
    keyboard=[
        [KeyboardButton(text="Мониторить все")],
        [KeyboardButton(text="Мониторить последние")],
        [KeyboardButton(text="Мониторить Определенные")],
        [KeyboardButton(text="Остановить сканер")]
    ]
)

def return_gift_menu(link):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Portals", url=link)]
    ])

return_buttons = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[KeyboardButton(text="Назад")]])
