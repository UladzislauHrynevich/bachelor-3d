# bachelor-3d — контекст для Claude

## Цель
Бакалаврская работа (STU Bratislava): Interactive Novel View Synthesis for Telepresence using 3D Gaussian Splatting.
Исследовательский вопрос: как число входных изображений (300/200/150/100/75/50) влияет на качество (PSNR, SSIM, LPIPS) и стоимость (время обучения, пиковая VRAM, число зарегистрированных камер) реконструкции 3DGS, и могут ли параметры обучения компенсировать меньшее число кадров.

## Стек
FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pytest, FFmpeg, COLMAP, PyTorch, gsplat. Локально Arch Linux + venv (`.venv`, Python 3.14). GPU-обучение только в Google Colab (основной) / Kaggle (запасной), локальной NVIDIA GPU нет.

Локально (проверено 2026-11-12): fastapi 0.141.1, sqlalchemy 2.0.54, alembic 1.20.0, psycopg 3.3.6, uvicorn 0.53.0, httpx 0.28.1, python-multipart 0.0.32, pytest 9.1.1. FFmpeg есть (`/usr/bin/ffmpeg`). COLMAP локально НЕ установлен. torch/gsplat в локальном venv нет.
Файла зависимостей (requirements.txt / pyproject.toml) в репо НЕТ.

## Структура репо
```
backend/
  main.py                  FastAPI app (внимание: app создаётся и роутеры подключаются дважды)
  project_manager.py
  database/                database.py (engine/Base), models.py: Project, ProjectImage, ProcessingJob
  routers/projects.py      POST /projects, POST /projects/{id}/images, GET /projects/{id}/input (ZIP)
  routers/processing.py    POST /projects/{id}/process, POST /processing-jobs/claim,
                           POST /processing-jobs/{id}/complete|fail|retry,
                           POST|GET /processing-jobs/{id}/result, GET /processing-jobs/{id}
  services/                project_service, image_service, processing_service;
                           video_service.py — пустой, не в git
  worker/worker.py         claim → скачать ZIP → create_test_result (только metadata.json) → upload → complete/fail
  worker/pipeline.py       run_colmap (feature_extractor, exhaustive_matcher, mapper; CPU) — воркер его НЕ вызывает
alembic/versions/          projects, images, processing_jobs
tests/                     test_processing_api.py, test_processing_service.py, test_result_upload.py
scripts/                   upload_dataset.py (+ неотслеживаемые refactor_*.py)
docs/                      architecture.md, implementation-report-ru.md (не в git), colabe.md (пустой)
storage/projects/          загруженные данные (в .gitignore)
worker_data/, tmp/         рабочие файлы воркера (НЕ в .gitignore; worker_data частично закоммичен в add_colmap)
experiments/               результаты прогонов, формат см. experiments/README.md
```

## Состояние (проверено)
- Бэкенд: проекты, загрузка изображений, ZIP входа, очередь задач (claim/complete/fail/retry), загрузка/скачивание результата.
- pytest: 11 passed (2026-11-12, ветка add_colmap).
- Воркер прошёл end-to-end, но результат — ZIP с метаданными, НЕ 3DGS-модель.
- COLMAP South Building: 128/128 камер, ~84 573 точек, reproj error ~0.61 px (запуск вне локальной машины — локально colmap нет).
- Colab: PyTorch 2.14.1+cu130, CUDA True, gsplat 1.5.3 (pip). Сборка из исходников падала с code 137 (OOM) — не повторять.

## НЕ подтверждено / не реализовано
- CUDA-растеризация и backward в gsplat.
- Обучение реальной 3DGS-модели.
- Подключение pipeline.run_colmap к воркеру.
- Видео-эндпоинт POST /projects/{id}/video — НЕ реализован (в коде нет упоминаний video/ffmpeg). Проект: frame_count по умолчанию 300, максимум 2000, лимит видео 2 GB, извлечение кадров асинхронно в воркере.
- Frontend / web-viewer, метрики PSNR/SSIM/LPIPS.

## Правила работы
- Общаться по-русски.
- Не заявлять, что что-то работает, без теста.
- Не переустанавливать рабочие зависимости и не перепроектировать бэкенд без необходимости.
- Перед изменениями читать существующий код; при ошибках анализировать реальные логи.
- Один конкретный шаг за раз.
- Методология: фиксированные held-out тестовые виды, без утечки между соседними кадрами, фиксировать seed, версии ПО, разрешение.
- После значимого шага дописывать запись в docs/PROGRESS.md.
- Тесты: `.venv/bin/python -m pytest -q` (системный python без pytest).
