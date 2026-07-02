"""Обработчики команд и сообщений Telegram-бота."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.keyboards import alternate_answer_keyboard, more_topics_keyboard, topic_keyboard
from nlp.pipeline import QAPipeline
from nlp.topics import TOPICS

logger = logging.getLogger(__name__)
router = Router()

# Состояние сессий пользователей (in-memory)
_user_sessions: dict[int, dict] = {}


def _get_session(user_id: int) -> dict:
    if user_id not in _user_sessions:
        _user_sessions[user_id] = {
            "last_question": "",
            "alt_index": 0,
            "result": None,
        }
    return _user_sessions[user_id]


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Здравствуйте! Я бот-помощник по обращениям граждан "
        "в сфере общественного транспорта Ленинградской области.\n\n"
        "Опишите вашу проблему или вопрос — например:\n"
        "• «На маршруте 529 автобусы ходят редко»\n"
        "• «На маршруте 18 нет безналичной оплаты»\n"
        "• «Водитель маршрута 205А пропустил остановку»\n\n"
        "Ответ формируется на основе официальных шаблонов с помощью NLP и LM Studio."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    topics = "\n".join(f"• {t}" for t in TOPICS)
    await message.answer(
        f"Я могу помочь с обращениями по темам:\n{topics}\n\n"
        "Просто напишите вопрос текстом. Команды:\n"
        "/start — приветствие\n"
        "/help — справка\n"
        "/topics — выбрать тему вручную"
    )


@router.message(Command("topics"))
async def cmd_topics(message: Message) -> None:
    await message.answer("Выберите тему обращения:", reply_markup=topic_keyboard())


@router.callback_query(F.data.startswith("topic:"))
async def on_topic_select(callback: CallbackQuery, pipeline: QAPipeline) -> None:
    data = callback.data or ""
    if data == "topic:more":
        await callback.message.edit_reply_markup(reply_markup=more_topics_keyboard())  # type: ignore[union-attr]
        await callback.answer()
        return

    idx = int(data.split(":")[1])
    topic = TOPICS[idx]
    session = _get_session(callback.from_user.id)

    if not session["last_question"]:
        await callback.answer("Сначала отправьте текст вопроса", show_alert=True)
        return

    await callback.answer(f"Тема: {topic}")
    result = pipeline.process(session["last_question"], topic_override=topic)
    session["result"] = result
    session["alt_index"] = result.selected_index

    has_more = len(result.candidates) > 1
    await callback.message.answer(  # type: ignore[union-attr]
        result.answer,
        reply_markup=alternate_answer_keyboard(has_more),
    )
    await callback.message.answer(f"_{result.meta}_", parse_mode="Markdown")  # type: ignore[union-attr]


@router.callback_query(F.data == "alt:next")
async def on_alternate(callback: CallbackQuery, pipeline: QAPipeline) -> None:
    session = _get_session(callback.from_user.id)
    result = session.get("result")
    if not result or not session["last_question"]:
        await callback.answer("Нет предыдущего вопроса", show_alert=True)
        return

    session["alt_index"] = (session["alt_index"] + 1) % len(result.candidates)
    new_result = pipeline.process(
        session["last_question"],
        candidate_index=session["alt_index"],
    )
    session["result"] = new_result

    await callback.answer("Альтернативный вариант")
    has_more = len(new_result.candidates) > 1
    await callback.message.answer(  # type: ignore[union-attr]
        new_result.answer,
        reply_markup=alternate_answer_keyboard(has_more),
    )


@router.callback_query(F.data == "action:topics")
async def on_action_topics(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Выберите тему:", reply_markup=topic_keyboard())  # type: ignore[union-attr]


@router.message(F.text)
async def on_question(message: Message, pipeline: QAPipeline) -> None:
    question = (message.text or "").strip()
    if len(question) < 10:
        await message.answer("Пожалуйста, опишите вопрос подробнее (минимум 10 символов).")
        return

    session = _get_session(message.from_user.id)
    session["last_question"] = question
    session["alt_index"] = 0

    wait_msg = await message.answer("Обрабатываю обращение...")

    try:
        result = pipeline.process(question)
        session["result"] = result

        has_more = len(result.candidates) > 1
        await wait_msg.edit_text(
            result.answer,
            reply_markup=alternate_answer_keyboard(has_more),
        )
        await message.answer(f"_{result.meta}_", parse_mode="Markdown")
    except Exception as exc:
        logger.exception("Ошибка обработки вопроса")
        await wait_msg.edit_text(
            f"Произошла ошибка при обработке. Попробуйте позже.\n({exc})"
        )
