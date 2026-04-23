import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import start_router

# Настраиваем логирование, чтобы видеть запуск бота и возможные ошибки
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("Критическая ошибка: BOT_TOKEN не установлен! Пожалуйста, укажите его в файле .env")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрация всех роутеров
    dp.include_router(start_router)

    # Удаляем вебхуки, если они были, и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Бот SkyWatcher успешно запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот SkyWatcher остановлен.")
