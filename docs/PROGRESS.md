# Журнал прогресса

Формат записи: дата / что сделано / что проверено и как / цифры / следующий шаг.
Новые записи — сверху.

---

## 2026-11-12

**Что сделано**
- Аудит репозитория (ветка `add_colmap`), созданы CLAUDE.md, docs/PROGRESS.md, experiments/README.md; правила в .gitignore. Код проекта не менялся.

**Что проверено и как**
- `.venv/bin/python -m pytest -v` → все тесты прошли.
- Видео-эндпоинт: `grep -rni -e video -e ffmpeg backend tests scripts alembic` → совпадений нет. `POST /projects/{id}/video` не существует; `backend/services/video_service.py` пустой (0 байт, не в git).
- Воркер (`backend/worker/worker.py`) вызывает `create_test_result` (только metadata.json); `pipeline.run_colmap` нигде не вызывается.
- Локально: `colmap` не найден в PATH, `ffmpeg` есть; torch/gsplat в venv нет.
- requirements.txt / pyproject.toml отсутствуют.

**Цифры**
- pytest: 11 passed, 2 warnings (deprecation в starlette/httpx), 0.87 s. Python 3.14.7.
- Миграции alembic: 3 (projects, images, processing_jobs).

**Следующий шаг**
- Реализовать POST /projects/{id}/video (лимит 2 GB, frame_count 300 по умолчанию, макс. 2000; извлечение кадров в воркере через FFmpeg) — либо сначала подключить run_colmap к воркеру. Выбрать одно.
