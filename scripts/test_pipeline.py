"""Быстрый тест NLP-пайплайна без Telegram."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nlp.pipeline import QAPipeline

QUESTIONS = [
    "На маршруте 529 автобусы ходят редко, расписание не соблюдается",
    "В пригородных автобусах 18 и 100 отсутствует возможность безналичной оплаты",
    "Водитель маршрута 205А пропустил остановку",
]

pipeline = QAPipeline()
pipeline.initialize()

for q in QUESTIONS:
    print("=" * 60)
    print("Q:", q)
    result = pipeline.process(q)
    print("Meta:", result.meta)
    print("Answer:", result.answer[:400], "...")
    print()
