"""Извлечение сущностей из вопроса пользователя."""

from __future__ import annotations

import re
from typing import Any

ROUTE_RE = re.compile(
    r"(?:маршрут|автобус|рейс|маршрутк)[а-я]*\s*№?\s*(\d+\s*[А-Яа-яA-Za-z]?)",
    re.IGNORECASE,
)
ROUTE_PAIR_RE = re.compile(
    r"(\d{1,3}[А-Яа-яA-Za-z]?)\s+и\s+(\d{1,3}[А-Яа-яA-Za-z]?)",
    re.IGNORECASE,
)
PLATE_RE = re.compile(r"[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}", re.IGNORECASE)

PLACES = [
    "Санкт-Петербург", "СПб", "Кудрово", "Гатчина", "Тосно", "Выборг", "Всеволожск",
    "Сосновый Бор", "Кингисепп", "Луга", "Тихвин", "Кириши", "Волхов", "Сертолово",
    "Мурино", "Волосово", "Сланцы", "Приозерск", "Лодейное Поле", "Пикалёво",
    "Сиверский", "Коммунар", "Никольское", "Отрадное", "Сясьстрой", "Шлиссельбург",
    "Светогорск", "Подпорожье", "Бокситогорск", "Сясьстрой", "Оккервиль",
    "Дыбенко", "Ленобласть", "Ленинградская область",
]


def _normalize_route(raw: str) -> str:
    return re.sub(r"\s+", "", raw).upper()


def extract_entities(text: str) -> dict[str, list[str]]:
    routes: list[str] = []
    for match in ROUTE_RE.finditer(text):
        route = _normalize_route(match.group(1))
        if route and route not in routes:
            routes.append(route)

    for match in ROUTE_PAIR_RE.finditer(text):
        for g in match.groups():
            route = _normalize_route(g)
            if route and route not in routes:
                routes.append(route)

    if not routes:
        for match in re.finditer(r"№\s*(\d+\s*[А-Яа-яA-Za-z]?)", text):
            route = _normalize_route(match.group(1))
            if route and route not in routes:
                routes.append(route)

    places = [p for p in PLACES if p.lower() in text.lower()]

    carriers = []
    carrier_match = re.findall(r"ООО\s+[«\"]?[^»\"]+[»\"]?", text, re.IGNORECASE)
    carriers.extend(carrier_match)

    plates = PLATE_RE.findall(text)

    return {
        "routes": routes[:5],
        "places": places[:5],
        "carriers": carriers[:3],
        "plates": plates[:3],
    }


def entities_to_dict(entities: dict[str, list[str]]) -> dict[str, Any]:
    return {k: v for k, v in entities.items() if v}
