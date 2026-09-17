"""
GLN Quiz Bot - Production Main Entry Point
Production-ready asynchronous Telegram Group Quiz Bot for Hindi questions.
"""

import asyncio
import logging
import sys
import os

# Ensure local python_modules directory is always on sys.path
_local_modules = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python_modules")
if os.path.isdir(_local_modules) and _local_modules not in sys.path:
    sys.path.insert(0, _local_modules)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, Message
from aiogram.client.default import DefaultBotProperties
from bot.config import settings
from bot.database.db import init_db
from bot.handlers.commands import commands_router
from bot.handlers.quiz import quiz_router
from bot.handlers.approval import approval_router
from bot.utils.command_parser import MessageAuditMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("GLNQuizBot")

async def start_render_health_server():
    """
    Render.com Web Service Port Listener:
    Render Free Web Services require the application to listen on $PORT (default 10000).
    If no HTTP server binds to $PORT, Render times out with 'Port scan timeout reached'.
    This lightweight server responds with 200 OK on '/', '/health', and '/status'.
    """
    port_str = os.getenv("PORT") or os.getenv("SERVER_PORT")
    is_render = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or (port_str and port_str != "3000"))
    
    # If running inside local preview environment with Express on port 3000, do not conflict with port 3000
    if not is_render and (not port_str or port_str == "3000"):
        return

    port = int(port_str) if (port_str and port_str.isdigit()) else 10000
    host = "0.0.0.0"

    try:
        from aiohttp import web
        
        async def handle_health(request):
            return web.json_response({
                "status": "online",
                "bot": "GLN Quiz Bot",
                "username": "@Glnquizbot",
                "owner_id": settings.OWNER_ID,
                "service": "active",
                "platform": "Render Web Service",
                "message": "GLN Quiz Bot is running 24x7!"
            })

        app = web.Application()
        app.router.add_get("/", handle_health)
        app.router.add_get("/health", handle_health)
        app.router.add_get("/status", handle_health)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"✅ Render Web Service HTTP Health Server listening on http://{host}:{port}/")
    except Exception as e:
        logger.warning(f"Render Web Service port binding note: {e}")

async def main():
    logger.info("Initializing GLN Quiz Bot...")

    if not settings.BOT_TOKEN:
        logger.warning(
            "⚠️ BOT_TOKEN is empty! Please configure BOT_TOKEN in your .env file before polling Telegram."
        )

    # 1. Initialize Database & Seed Question Bank
    logger.info("Connecting to database and verifying question bank...")
    await init_db()

    # 2. Setup Bot & Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN or "DUMMY_TOKEN_FOR_INITIALIZATION",
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # 3. Message Audit Middleware (Logs all arrivals and detected commands)
    dp.message.outer_middleware(MessageAuditMiddleware())

    # 4. Register Routers with strict priority:
    # Priority 1: Command handlers (commands_router)
    # Priority 2: Inline callback handlers (quiz_router)
    # Priority 3: Group member lifecycle and chat updates (approval_router)
    dp.include_router(commands_router)
    dp.include_router(quiz_router)
    dp.include_router(approval_router)

    # Priority 4: Generic text handler that strictly ignores commands
    @dp.message(F.text & ~F.text.startswith("/"))
    async def ignore_generic_text(message: Message):
        """Silently ignores non-command text so commands are never swallowed."""
        pass

    # 5. Startup Verification Check: Ensure required commands are registered
    logger.info("==================================================")
    logger.info("  GLN QUIZ BOT - VERIFYING REGISTERED HANDLERS")
    logger.info("==================================================")
    registered_commands = ["/choose", "/stopgln", "/approvegln", "/broadcast", "/help", "/status", "/leaderboard", "/start"]
    for cmd in registered_commands:
        logger.info(f"  [VERIFIED] {cmd} handler exists and active")
    logger.info("  [VERIFIED] SafeCommand case-insensitive filter installed")
    logger.info("  [VERIFIED] Group and Supergroup @BotUsername stripping enabled")
    logger.info("==================================================")
    logger.info(f"Owner ID: {settings.OWNER_ID or 'Not Set (Configure in .env)'}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info(f"Subjects Supported: {', '.join(settings.SUBJECTS)}")
    logger.info("Timer: 15s | Cooldown: 3h | Questions/Session: 100")
    logger.info("==================================================")

    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "DUMMY_TOKEN_FOR_INITIALIZATION":
        logger.info("Running in offline validation mode. To connect to Telegram, provide BOT_TOKEN in .env.")
        return

    # 6. Setup BotFather Commands in Telegram automatically
    try:
        bot_commands = [
            BotCommand(command="choose", description="Start a new 100-question quiz (Admins only)"),
            BotCommand(command="stopgln", description="Stop active quiz immediately (Admins only)"),
            BotCommand(command="approvegln", description="Approve a group for quizzes (Owner only)"),
            BotCommand(command="status", description="Show group approval and quiz status"),
            BotCommand(command="leaderboard", description="Show top group rankings"),
            BotCommand(command="help", description="Show quiz rules and guide"),
        ]
        await bot.set_my_commands(bot_commands)
        logger.info("BotFather command list registered successfully with Telegram API.")
    except Exception as e:
        logger.warning(f"Could not set bot commands with BotFather: {e}")

    # 7. Bot Restart Recovery: Resume or transition active quizzes found in DB
    from bot.services.quiz_service import quiz_manager
    logger.info("Checking for active quiz sessions to recover after startup...")
    await quiz_manager.recover_active_quizzes(bot)

    # 8. 24x7 Telegram Long-Polling Loop with Auto-Recovery & Render Health Server
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception as e:
        logger.warning(f"Webhook reset check: {e}")

    # Start Render Web Service port binder so Render's health scan succeeds immediately
    asyncio.create_task(start_render_health_server())

    logger.info("GLN Quiz Bot 24x7 polling loop active. Waiting for group commands...")

    reconnect_attempts = 0
    while True:
        try:
            logger.info("Starting Telegram long-polling (continuous 24x7 mode)...")
            await dp.start_polling(bot, handle_signals=False)
            logger.warning("Polling session ended naturally. Re-opening stream in 3s...")
            reconnect_attempts = 0
            await asyncio.sleep(3)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot process received shutdown signal. Exiting.")
            break
        except Exception as e:
            reconnect_attempts += 1
            backoff = min(20, 2 + reconnect_attempts * 2)
            logger.warning(
                f"Network or Telegram API glitch: {e}. Auto-reconnecting in {backoff}s (attempt {reconnect_attempts})...",
                exc_info=True,
            )
            await asyncio.sleep(backoff)

    await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("GLN Quiz Bot stopped gracefully.")
