"""Парсинг DOCX-шаблонов ответов гражданам."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docx import Document

from nlp.topics import TOPIC_KEYWORDS

ROUTE_RE = re.compile(r"маршрут\s*№?\s*(\d+\s*[А-Яа-яA-Za-z]?)", re.IGNORECASE)
CARRIER_RE = re.compile(
    r"(ООО\s+[«\"]?[\w\-\s]+[»\"]?|АО\s+[«\"]?[\w\-\s]+[»\"]?|"
    r"«[\w\-\s]+»|ИП\s+[\w\-\s]+)",
    re.IGNORECASE,
)
PHONE_RE = re.compile(r"(?:\+7|8)?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}|309-10-10|408-04-40")
LINK_RE = re.compile(r"https?://\S+|www\.\S+")
SPLIT_RE = re.compile(
    r"(?=(?:^|\n)(?:Уважаем(?:ый|ая)|Добрый день|Здравствуйте|"
    r"В ответ на Ваше обращение|В ответ на ваше обращение))",
    re.IGNORECASE | re.MULTILINE,
)


def _detect_topics(text: str) -> list[str]:
    lower = text.lower()
    found = [topic for topic, keywords in TOPIC_KEYWORDS.items() if any(kw in lower for kw in keywords)]
    return found or ["Указание маршрута"]


def _extract_routes(text: str) -> list[str]:
    routes = []
    for match in ROUTE_RE.finditer(text):
        route = re.sub(r"\s+", "", match.group(1)).upper()
        if route and route not in routes:
            routes.append(route)
    return routes


def _extract_carriers(text: str) -> list[str]:
    carriers = []
    for match in CARRIER_RE.finditer(text):
        carrier = match.group(1).strip()
        if len(carrier) > 4 and carrier not in carriers:
            carriers.append(carrier)
    return carriers[:5]


def _chunk_metadata(text: str) -> dict[str, Any]:
    return {
        "route_numbers": _extract_routes(text),
        "carriers": _extract_carriers(text),
        "topics": _detect_topics(text),
        "phones": PHONE_RE.findall(text),
        "links": LINK_RE.findall(text),
        "is_rejection": "отклон" in text.lower() or "повторн" in text.lower(),
    }


def parse_docx_templates(path: Path) -> list[dict[str, Any]]:
    doc = Document(str(path))
    full_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())

    raw_chunks = [c.strip() for c in SPLIT_RE.split(full_text) if c.strip()]
    if not raw_chunks:
        raw_chunks = [full_text]

    templates: list[dict[str, Any]] = []
    for idx, text in enumerate(raw_chunks):
        if len(text) < 80:
            continue
        meta = _chunk_metadata(text)
        templates.append(
            {
                "id": idx,
                "text": text,
                **meta,
            }
        )

    return templates
