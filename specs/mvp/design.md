# MVP Design — Дневник снов

## Архитектура
FastAPI (webhook) + Aiogram 3.x + PostgreSQL + Redis + OpenAI-compatible LLM

## Поток интерпретации
1. Пользователь → текст/голос
2. Whisper (если голос)
3. LLM с системным промтом
4. Валидация JSON + стоп-слова
5. Retry с усиленным промтом при эзотерике
6. Сохранение в БД (AES-256)
7. Ответ + inline-кнопки

## Модели данных
- users — профиль Telegram-пользователя
- dreams — зашифрованные сны + интерпретация JSONB
- feedback — оценки точности
