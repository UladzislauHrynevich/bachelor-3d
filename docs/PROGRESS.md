# Журнал прогресса

Формат записи: дата / что сделано / что проверено и как / цифры / следующий шаг.
Новые записи — сверху.

---

## 2026-11-12 — шаг A: загрузка видео и извлечение кадров

**Что сделано**
- Новые файлы: `backend/routers/videos.py`, `backend/services/video_service.py`, `tests/test_video_upload.py`. В `backend/main.py` добавлены 2 строки (import + include_router). Существующий код, модели и миграции не менялись.
- `POST /projects/{id}/video` (multipart: `video`, `frame_count` 10..2000, по умолчанию 300). Потоковое сохранение кусками по 1 MB в `storage/projects/<id>/videos/<video_id>/source.<ext>`, лимит 2 GB → 413, ffprobe без видеопотока → 400, извлечение — FastAPI BackgroundTasks.
- `GET /projects/{id}/videos/{video_id}` → video.json (статусы uploaded/extracting/done/failed), запись атомарно через os.replace.
- `extract_frames(project_id, video_id)` не зависит от HTTP (можно вызвать из воркера). Кадры: `<project>/input/vid_<8>_f<index:06d>.jpg`, без ресайза, `-q:v 2`; frames.json; ProjectImage-записи одной транзакцией; при ошибке rollback + удаление кадров + status=failed с stderr.
- Индексы: `floor((i+0.5)*T/n)` в целочисленной арифметике. В ffmpeg — формула постоянной длины `C(k)=floor((2kN+T-1)/2T)`, кадр k берётся при `C(k+1)>C(k)`.

**Что проверено и как**
- Первая версия (`select='eq(n,a)+eq(n,b)+…'`) падала уже на 120 кадрах: ffmpeg «Error while parsing expression … Cannot allocate memory» (предел глубины парсера). Заменено формулой; эквивалентность с Python-индексами проверена перебором всех T<400, N≤T и случаем T=108000, N=2000.
- pytest: старые 11 тестов не менялись и прошли; новые 22 — точное число кадров и равномерные уникальные индексы, frame_count>total → все кадры, не-видео и аудио → 400, 0/9/2001/5000 → 422, 413 с удалением файла, 404, кадры в ZIP `/input`, rollback при ошибке БД, пиксельное совпадение кадров с прямым извлечением по индексу, 2000 из 2100 кадров.
- Живой прогон uvicorn + PostgreSQL + curl: 20 кадров из 120, 20 строк в `images`, 20 файлов в ZIP.

**Цифры**
- pytest: 33 passed (11 старых + 22 новых), 2 warnings, ~3.5 s.
- 2000 кадров (64x48, 70 с) извлекаются за ~0.8 s.

**Ограничения (не проверено)**
- total_frames = число пакетов (`-count_packets`); для VFR-видео timestamp_s = index/fps приблизителен.
- Реальные видео с телефона (HEVC, поворот) и файлы ~2 GB не проверялись.
- BackgroundTasks выполняется в процессе API: при перезапуске сервера статус останется `extracting`.

**Следующий шаг**
- Подключить `pipeline.run_colmap` к воркеру вместо `create_test_result`.

---

## 2026-11-12 — аудит

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
