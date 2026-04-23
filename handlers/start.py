from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from config import WEB_APP_URL

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    # Создаем Reply-клавиатуру с кнопкой Web App
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Открыть карту 🛰", web_app=WebAppInfo(url=WEB_APP_URL))]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "Приветствую, Командир. Я система мониторинга воздушных угроз SkyWatcher. 🛸\n\n"
        "Для просмотра текущей обстановки в режиме реального времени нажмите кнопку ниже.",
        reply_markup=markup
    )
