"""Сборка финального ответа из шаблона."""

from __future__ import annotations

import re
from typing import Any

from config import settings


def _replace_routes(text: str, routes: list[str]) -> str:
    if not routes:
        return text
    primary = routes[0]

    def repl(match: re.Match[str]) -> str:
        return match.group(0).replace(match.group(1), primary)

    return ROUTE_RE.sub(repl, text, count=1)


ROUTE_RE = re.compile(r"(маршрут\s*№?\s*)(\d+\s*[А-Яа-яA-Za-z]?)", re.IGNORECASE)


def build_fallback_answer(question: str, topics: list[str]) -> str:
    topics_str = ", ".join(topics) if topics else "общий вопрос"
    return (
        f"Благодарим за обращение. По теме «{topics_str}» точного шаблона ответа не найдено.\n\n"
        f"Для получения официального ответа обратитесь на горячую линию: {settings.hotline} "
        f"или через форму обратной связи на сайте transport.lenobl.ru.\n\n"
        f"Ваш вопрос: {question[:300]}"
    )


def apply_slots(template_text: str, entities: dict[str, list[str]]) -> str:
    text = template_text
    routes = entities.get("routes", [])
    if routes:
        text = _replace_routes(text, routes)
    if routes and "маршрут" not in text.lower()[:100]:
        text = f"По Вашему обращению в отношении маршрута №{routes[0]}:\n\n{text}"
    return text.strip()


def format_response_meta(
    topics: list[str],
    entities: dict[str, list[str]],
    score: float,
    used_lm_studio: bool,
) -> str:
    parts = []
    if topics:
        parts.append(f"Темы: {', '.join(topics)}")
    if entities.get("routes"):
        parts.append(f"Маршрут: {', '.join(entities['routes'])}")
    parts.append(f"Релевантность: {score:.0%}")
    if used_lm_studio:
        parts.append("LLM: LM Studio")
    return " | ".join(parts)
