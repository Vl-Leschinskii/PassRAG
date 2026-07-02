"""Классификация тем обращения (embedding similarity + keyword boost)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from config import PROCESSED_DIR, settings
from nlp.topics import TOPIC_DESCRIPTIONS, TOPIC_KEYWORDS, TOPICS

logger = logging.getLogger(__name__)


class TopicClassifier:
    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None
        self._topic_embeddings: np.ndarray | None = None
        self._training_questions: list[dict[str, Any]] = []

    def _ensure_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Загрузка модели эмбеддингов: %s", settings.embedding_model)
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def load_training_data(self) -> None:
        labels_path = PROCESSED_DIR / "labels.json"
        if labels_path.exists():
            data = json.loads(labels_path.read_text(encoding="utf-8"))
            self._training_questions = data.get("questions", [])

    def _topic_texts(self) -> list[str]:
        return [f"{topic}: {TOPIC_DESCRIPTIONS.get(topic, topic)}" for topic in TOPICS]

    def _encode(self, texts: list[str], prefix: str) -> np.ndarray:
        model = self._ensure_model()
        prefixed = [f"{prefix}: {t}" for t in texts]
        return model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)

    def _ensure_topic_embeddings(self) -> np.ndarray:
        if self._topic_embeddings is None:
            self._topic_embeddings = self._encode(self._topic_texts(), "passage")
        return self._topic_embeddings

    def _keyword_scores(self, text: str) -> dict[str, float]:
        lower = text.lower()
        scores: dict[str, float] = {}
        for topic, keywords in TOPIC_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in lower)
            if hits:
                scores[topic] = min(1.0, hits * 0.5)
        return scores

    def _training_boost(self, text: str) -> dict[str, float]:
        if not self._training_questions:
            return {}
        model = self._ensure_model()
        q_emb = model.encode(f"query: {text}", normalize_embeddings=True, show_progress_bar=False)
        boosts: dict[str, float] = {}
        for item in self._training_questions:
            t_emb = model.encode(
                f"passage: {item['question']}",
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            sim = float(np.dot(q_emb, t_emb))
            if sim > 0.65:
                for label in item.get("labels", []):
                    boosts[label] = max(boosts.get(label, 0), sim * 0.5)
        return boosts

    def classify(self, text: str, threshold: float | None = None) -> list[tuple[str, float]]:
        threshold = threshold if threshold is not None else settings.confidence_threshold
        topic_embs = self._ensure_topic_embeddings()
        q_emb = self._encode([text], "query")[0]

        scores: dict[str, float] = {}
        for i, topic in enumerate(TOPICS):
            scores[topic] = float(np.dot(q_emb, topic_embs[i]))

        for topic, boost in self._keyword_scores(text).items():
            scores[topic] = min(1.0, scores.get(topic, 0) + boost)

        for topic, boost in self._training_boost(text).items():
            scores[topic] = min(1.0, scores.get(topic, 0) + boost)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(t, s) for t, s in ranked if s >= threshold]

    def top_topics(self, text: str, n: int = 3) -> list[str]:
        ranked = self.classify(text, threshold=0.0)
        return [t for t, _ in ranked[:n]]
