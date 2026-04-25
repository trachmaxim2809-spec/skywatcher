import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import start_router
from database_manager import init_firebase

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Простейший веб-сервер для Render Health Check
async def handle(request):
    return web.Response(text="SkyWatcher Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080)) # Render передает порт в переменную PORT
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Веб-сервер запущен на порту {port}")

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("Критическая ошибка: BOT_TOKEN не установлен!")
        return

    # Инициализация Firebase
    init_firebase()

    # Запускаем веб-сервер в фоне

    await start_web_server()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start_router)
    
    from handlers.bot_logic import router as bot_logic_router
    dp.include_router(bot_logic_router)

    from aiogram.types import MenuButtonWebApp, WebAppInfo
    from config import WEB_APP_URL
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Карта 🛰", web_app=WebAppInfo(url=WEB_APP_URL))
    )

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот SkyWatcher успешно запущен!")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот SkyWatcher остановлен.")
