"""RAG: FAISS-индекс и поиск шаблонов."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import INDEX_DIR, PROCESSED_DIR, settings

logger = logging.getLogger(__name__)


class TemplateRetriever:
    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None
        self._index: faiss.Index | None = None
        self._templates: list[dict[str, Any]] = []

    def _ensure_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Загрузка модели эмбеддингов: %s", settings.embedding_model)
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def load(self) -> None:
        templates_path = PROCESSED_DIR / "templates.json"
        index_path = INDEX_DIR / "faiss.index"

        if not templates_path.exists() or not index_path.exists():
            raise FileNotFoundError(
                "Индекс не найден. Запустите: python scripts/build_index.py"
            )

        self._templates = json.loads(templates_path.read_text(encoding="utf-8"))
        index_bytes = np.frombuffer(index_path.read_bytes(), dtype=np.uint8)
        self._index = faiss.deserialize_index(index_bytes)
        logger.info("Загружено шаблонов: %d", len(self._templates))

    @property
    def is_ready(self) -> bool:
        return self._index is not None and bool(self._templates)

    def _encode_query(self, text: str) -> np.ndarray:
        model = self._ensure_model()
        emb = model.encode(f"query: {text}", normalize_embeddings=True, show_progress_bar=False)
        return np.array([emb], dtype=np.float32)

    def _filter_score(
        self,
        template: dict[str, Any],
        topics: list[str],
        routes: list[str],
    ) -> float:
        bonus = 0.0
        if routes:
            tpl_routes = {re.sub(r"\s+", "", r).upper() for r in template.get("route_numbers", [])}
            user_routes = {re.sub(r"\s+", "", r).upper() for r in routes}
            if tpl_routes & user_routes:
                bonus += 0.25
            elif tpl_routes and not (tpl_routes & user_routes):
                bonus -= 0.1
        if topics:
            tpl_topics = set(template.get("topics", []))
            overlap = tpl_topics & set(topics)
            bonus += 0.05 * len(overlap)
        return bonus

    def search(
        self,
        question: str,
        topics: list[str] | None = None,
        routes: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.is_ready:
            self.load()

        top_k = top_k or settings.top_k
        topics = topics or []
        routes = routes or []

        assert self._index is not None
        query_emb = self._encode_query(question)
        scores, indices = self._index.search(query_emb, min(top_k * 5, len(self._templates)))

        results: list[dict[str, Any]] = []
        seen_texts: set[str] = set()

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            template = self._templates[idx]
            text_key = template["text"][:200]
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            final_score = float(score) + self._filter_score(template, topics, routes)
            results.append({**template, "score": final_score, "embedding_score": float(score)})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
