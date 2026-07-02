"""Точка входа Telegram-бота."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.handlers import router  # noqa: E402
from config import settings  # noqa: E402
from nlp.pipeline import QAPipeline  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not settings.bot_token:
        logger.error("Укажите BOT_TOKEN в файле .env")
        sys.exit(1)

    pipeline = QAPipeline()
    logger.info("Инициализация NLP-пайплайна...")
    pipeline.initialize()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    dp["pipeline"] = pipeline

    logger.info("Бот запущен")
    await dp.start_polling(bot, pipeline=pipeline)


if __name__ == "__main__":
    asyncio.run(main())
