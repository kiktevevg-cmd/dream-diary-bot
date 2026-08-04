# Дневник снов (Dream Diary)

Telegram-бот для психологической интерпретации сновидений на основе научных подходов.

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните переменные:
   ```bash
   cp .env.example .env
   ```

2. Сгенерируйте ключ шифрования:
   ```python
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. Запустите через Docker:
   ```bash
   docker-compose up --build
   ```

4. Проверьте health:
   ```bash
   curl http://localhost:8000/health
   ```

## Локальная разработка (polling)

```bash
pip install -r requirements.txt
python -m app.polling
```

## Тесты

```bash
pytest tests/ -v
```

## Стек

- **Backend:** FastAPI + Aiogram 3.x
- **БД:** PostgreSQL + SQLAlchemy async
- **Кеш:** Redis
- **LLM:** OpenAI-compatible API
- **Голос:** Whisper API

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/interpret` | Интерпретация сна |
| `/history` | Последние 10 снов |
| `/stats` | Эмоциональная динамика |
| `/insights` | Паттерны и образы |
| `/settings` | Настройки |
| `/clear` | Удалить историю |
| `/delete_my_data` | Полное удаление данных |

## Деплой на Railway

1. Создайте проект на [railway.app](https://railway.app) из GitHub-репозитория
2. Добавьте плагины **PostgreSQL** и **Redis** — Railway автоматически проставит `DATABASE_URL` и `REDIS_URL`
3. Задайте переменные окружения:
   - `BOT_TOKEN` — токен Telegram-бота
   - `LLM_API_KEY` — ключ OpenAI (или совместимого API)
   - `ENCRYPTION_KEY` — ключ шифрования (32+ символов)
   - `WEBHOOK_URL` — публичный URL Railway (например `https://your-app.up.railway.app`)
   - `WEBHOOK_SECRET` — произвольная строка для защиты webhook
   - `ENVIRONMENT=production`
4. Railway соберёт Docker-образ и запустит бота в webhook-режиме
5. Проверьте: `https://your-app.up.railway.app/health`
