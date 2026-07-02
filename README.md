# PassRAG

Telegram NLP-бот для ответов гражданам по общественному транспорту Ленинградской области.

**RAG** (Retrieval-Augmented Generation) по официальным шаблонам из DOCX + **LM Studio** как локальный LLM-сервер.

## Архитектура

```
Вопрос → NER (маршрут, место) → Классификатор тем → RAG (FAISS) → LM Studio → Ответ
```

- **RAG** — поиск подходящего шаблона среди ~сотен ответов из DOCX
- **LM Studio** — выбор лучшего шаблона и адаптация текста под вопрос гражданина
- **sentence-transformers** — локальные эмбеддинги (без внешних API)

## Требования

- Python 3.10+
- [LM Studio](https://lmstudio.ai/) с запущенным локальным сервером
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))

## Установка

```bash
git clone https://github.com/Vl-Leschinskii/PassRAG.git
cd PassRAG
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Настройка LM Studio

1. Установите и откройте **LM Studio**
2. Скачайте русскоязычную модель (рекомендуется `Qwen2.5-7B-Instruct`)
3. Загрузите модель в память (Load Model)
4. Перейдите на вкладку **Developer** (Local Server)
5. Нажмите **Start Server** — сервер запустится на `http://localhost:1234`
6. При необходимости укажите параметры в `.env`:

```env
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio
LM_STUDIO_MODEL=local-model
```

## Настройка бота

```bash
copy .env.example .env
```

Отредактируйте `.env`:

```env
BOT_TOKEN=your_telegram_bot_token
```

## Подготовка базы знаний

Положите в корень проекта исходные документы:
- `Важно. Ответы гражданам. Шаблоны.docx`
- `Вопросы разметка_последний.xlsx`

Затем выполните (один раз и при обновлении DOCX):

```bash
python scripts/build_index.py
```

Скрипт:
- парсит DOCX → `data/processed/templates.json`
- парсит XLSX → `data/processed/labels.json`
- строит FAISS-индекс в `data/index/`

## Запуск

1. Убедитесь, что LM Studio Server запущен
2. Запустите бота:

```bash
python -m bot.main
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и примеры вопросов |
| `/help` | Список тем и справка |
| `/topics` | Ручной выбор темы |
| Текст | Обработка обращения |

## Структура проекта

```
PassRAG/
├── bot/           # Telegram (aiogram 3)
├── nlp/           # NLP-пайплайн + LM Studio клиент
├── scripts/       # build_index.py, test_pipeline.py
├── data/          # processed/ и index/ (генерируются)
├── config.py
└── requirements.txt
```

## Примеры вопросов

- «На маршруте 529 автобусы ходят редко, расписание не соблюдается»
- «В пригородных автобусах 18 и 100 нет безналичной оплаты»
- «Водитель маршрута 205А пропустил остановку и был груб»

## Автор

[Vl-Leschinskii](https://github.com/Vl-Leschinskii)
