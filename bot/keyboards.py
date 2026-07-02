"""Inline-клавиатуры Telegram-бота."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from nlp.topics import TOPICS


def topic_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=topic, callback_data=f"topic:{i}")]
        for i, topic in enumerate(TOPICS[:6])
    ]
    buttons.append(
        [InlineKeyboardButton(text="Другие темы...", callback_data="topic:more")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def more_topics_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=topic, callback_data=f"topic:{i}")]
        for i, topic in enumerate(TOPICS[6:], start=6)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def alternate_answer_keyboard(has_more: bool) -> InlineKeyboardMarkup:
    buttons = []
    if has_more:
        buttons.append(
            [InlineKeyboardButton(text="Другой вариант ответа", callback_data="alt:next")]
        )
    buttons.append(
        [InlineKeyboardButton(text="Уточнить тему", callback_data="action:topics")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
