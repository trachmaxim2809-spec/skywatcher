from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from config import WEB_APP_URL
from database_manager import set_region_status

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

@router.message(Command("test_alarm"))
async def cmd_test_alarm(message: Message):
    # Разделяем сообщение на команду и аргументы
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /test_alarm [название региона]\nПример: /test_alarm Киев")
        return
        
    region_name = parts[1].strip()
    
    # Реверсивно (или просто) включаем тревогу
    # Для простоты: всегда ставим True.
    success = set_region_status(region_name, True)
    
    if success:
        await message.answer(f"🚨 Тестовая тревога запущена для региона: {region_name}.\nОткройте карту и проверьте консоль, сообщение должно прийти мгновенно!")
    else:
        await message.answer("❌ Ошибка при записи в Firebase. Проверьте логи сервера.")

