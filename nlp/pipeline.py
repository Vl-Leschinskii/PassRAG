"""Оркестрация NLP-пайплайна: NER → классификация → RAG → LM Studio."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from config import settings
from nlp.classifier import TopicClassifier
from nlp.lm_studio import LMStudioClient
from nlp.ner import extract_entities
from nlp.response_builder import apply_slots, build_fallback_answer, format_response_meta
from nlp.retrieval import TemplateRetriever

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    answer: str
    candidates: list[dict[str, Any]] = field(default_factory=list)
    selected_index: int = 0
    topics: list[str] = field(default_factory=list)
    entities: dict[str, list[str]] = field(default_factory=dict)
    score: float = 0.0
    used_lm_studio: bool = False
    meta: str = ""


class QAPipeline:
    def __init__(self) -> None:
        self.retriever = TemplateRetriever()
        self.classifier = TopicClassifier()
        self.lm_studio = LMStudioClient()
        self._lm_available: bool | None = None

    def initialize(self) -> None:
        self.retriever.load()
        self.classifier.load_training_data()
        self._lm_available = self.lm_studio.is_available()
        if self._lm_available:
            logger.info("LM Studio подключён")
        else:
            logger.warning("LM Studio недоступен — используется режим без LLM")

    def _lm_available_cached(self) -> bool:
        if self._lm_available is None:
            self._lm_available = self.lm_studio.is_available()
        return bool(self._lm_available)

    def process(
        self,
        question: str,
        topic_override: str | None = None,
        candidate_index: int | None = None,
    ) -> PipelineResult:
        entities = extract_entities(question)
        routes = entities.get("routes", [])

        if topic_override:
            topics = [topic_override]
        else:
            topics = self.classifier.top_topics(question, n=3)

        candidates = self.retriever.search(
            question,
            topics=topics,
            routes=routes,
            top_k=settings.top_k,
        )

        if not candidates:
            answer = build_fallback_answer(question, topics)
            return PipelineResult(
                answer=answer,
                topics=topics,
                entities=entities,
                meta=format_response_meta(topics, entities, 0.0, False),
            )

        best_score = candidates[0]["score"]
        if best_score < settings.confidence_threshold:
            answer = build_fallback_answer(question, topics)
            return PipelineResult(
                answer=answer,
                candidates=candidates,
                topics=topics,
                entities=entities,
                score=best_score,
                meta=format_response_meta(topics, entities, best_score, False),
            )

        used_lm = False
        if candidate_index is not None and 0 <= candidate_index < len(candidates):
            selected_idx = candidate_index
        elif self._lm_available_cached():
            selected_idx = self.lm_studio.select_template(
                question, candidates, topics, entities
            )
            used_lm = True
        else:
            selected_idx = 0

        template = candidates[selected_idx]
        base_text = apply_slots(template["text"], entities)

        if self._lm_available_cached():
            answer = self.lm_studio.adapt_answer(question, base_text, entities)
            used_lm = True
        else:
            answer = base_text

        return PipelineResult(
            answer=answer,
            candidates=candidates,
            selected_index=selected_idx,
            topics=topics,
            entities=entities,
            score=template["score"],
            used_lm_studio=used_lm,
            meta=format_response_meta(topics, entities, template["score"], used_lm),
        )
