"""Построение FAISS-индекса из DOCX и XLSX."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import INDEX_DIR, PROCESSED_DIR, settings  # noqa: E402
from nlp.ingestion.docx_parser import parse_docx_templates  # noqa: E402
from nlp.ingestion.xlsx_parser import parse_xlsx_labels  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Парсинг DOCX: %s", settings.docx_path.name)
    templates = parse_docx_templates(settings.docx_path)
    templates_path = PROCESSED_DIR / "templates.json"
    templates_path.write_text(
        json.dumps(templates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Сохранено шаблонов: %d", len(templates))

    logger.info("Парсинг XLSX: %s", settings.xlsx_path.name)
    labels = parse_xlsx_labels(settings.xlsx_path)
    labels_path = PROCESSED_DIR / "labels.json"
    labels_path.write_text(
        json.dumps(labels, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Сохранено вопросов: %d", len(labels["questions"]))

    logger.info("Построение эмбеддингов: %s", settings.embedding_model)
    model = SentenceTransformer(settings.embedding_model)
    texts = [f"passage: {t['text']}" for t in templates]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    index_path = INDEX_DIR / "faiss.index"
    serialized = faiss.serialize_index(index)
    index_path.write_bytes(serialized.tobytes())

    meta = {
        "count": len(templates),
        "dim": dim,
        "model": settings.embedding_model,
    }
    (INDEX_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Индекс сохранён: %s", INDEX_DIR / "faiss.index")


if __name__ == "__main__":
    main()
