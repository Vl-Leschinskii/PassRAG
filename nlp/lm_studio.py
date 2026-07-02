"""Клиент LM Studio через OpenAI-совместимый API."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

from config import settings

logger = logging.getLogger(__name__)


class LMStudioClient:
    def __init__(self) -> None:
        self._client = OpenAI(
            base_url=settings.lm_studio_base_url,
            api_key=settings.lm_studio_api_key,
            timeout=settings.lm_studio_timeout,
        )
        self._model = settings.lm_studio_model

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()

    def is_available(self) -> bool:
        try:
            models = self._client.models.list()
            return bool(models.data)
        except Exception as exc:
            logger.warning("LM Studio недоступен: %s", exc)
            return False

    def select_template(
        self,
        question: str,
        candidates: list[dict[str, Any]],
        topics: list[str],
        entities: dict[str, list[str]],
    ) -> int:
        """Выбор лучшего шаблона среди top-k кандидатов RAG."""
        if not candidates:
            return 0
        if len(candidates) == 1:
            return 0

        options = []
        for i, item in enumerate(candidates):
            preview = item["text"][:600].replace("\n", " ")
            options.append(
                f"[{i}] маршруты={item.get('route_numbers', [])}, "
                f"темы={item.get('topics', [])}, текст={preview}"
            )

        system = (
            "Ты помощник Комитета Ленинградской области по транспорту. "
            "Выбери номер шаблона ответа (0, 1 или 2), который лучше всего подходит "
            "для ответа на обращение гражданина. Отвечай ТОЛЬКО JSON: "
            '{"index": 0, "reason": "кратко"}'
        )
        user = (
            f"Вопрос гражданина: {question}\n"
            f"Определённые темы: {', '.join(topics) or 'не определены'}\n"
            f"Извлечённые сущности: {json.dumps(entities, ensure_ascii=False)}\n\n"
            "Кандидаты:\n" + "\n".join(options)
        )

        try:
            raw = self.chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
            )
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                idx = int(data.get("index", 0))
                if 0 <= idx < len(candidates):
                    return idx
        except Exception as exc:
            logger.warning("LM Studio select_template failed: %s", exc)

        return 0

    def adapt_answer(
        self,
        question: str,
        template_text: str,
        entities: dict[str, list[str]],
    ) -> str:
        """Адаптация шаблона под вопрос с сохранением официального стиля."""
        routes = ", ".join(entities.get("routes", [])) or "не указан"
        places = ", ".join(entities.get("places", [])) or "не указано"

        system = (
            "Ты сотрудник Комитета Ленинградской области по транспорту. "
            "На основе ГОТОВОГО шаблона составь официальный ответ гражданину. "
            "Правила:\n"
            "1. Сохраняй юридически корректный официальный тон\n"
            "2. НЕ выдумывай телефоны, ссылки, названия компаний — используй только из шаблона\n"
            "3. Если в шаблоне есть номер маршрута, а гражданин указал другой — "
            "адаптируй номер маршрута из вопроса\n"
            "4. Не сокращай важные части шаблона (контакты, ссылки, рекомендации)\n"
            "5. Ответ — только текст ответа, без пояснений"
        )
        user = (
            f"Вопрос гражданина: {question}\n"
            f"Маршрут из вопроса: {routes}\n"
            f"Населённый пункт: {places}\n\n"
            f"Шаблон ответа:\n{template_text}"
        )

        try:
            adapted = self.chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            if adapted and len(adapted) > 50:
                return adapted
        except Exception as exc:
            logger.warning("LM Studio adapt_answer failed: %s", exc)

        return template_text
