# Тесты: что проверяется и как это работает

## Запуск

```bash
.venv/bin/python -m pytest -q
```

Системный `python` без pytest, поэтому запуск только из `.venv`. Видео-тесты требуют `ffmpeg` и `ffprobe` в `PATH`, иначе они пропускаются (`skipif`).

Последний прогон: **47 passed** (2026-11-25, Python 3.14, fastapi 0.141.1, sqlalchemy 2.0.54, pytest 9.1.1, Arch Linux).

## Как устроено тестовое окружение

Тесты не трогают настоящую PostgreSQL, папку `storage/` и сеть.

| Что в приложении | Чем заменено в тестах | Где |
|---|---|---|
| PostgreSQL | SQLite в памяти (`sqlite+pysqlite:///:memory:` + `StaticPool`, чтобы все сессии видели одну базу); таблицы через `Base.metadata.create_all`, **без Alembic** | фикстуры `db` / `api` |
| Зависимость FastAPI `get_db` | `app.dependency_overrides[get_db]` отдаёт сессию тестовой базы | фикстура `api` |
| `storage/projects/<id>` | временная папка pytest `tmp_path` (подмена `get_project_directory` через `monkeypatch`) | фикстура `api` |
| HTTP-сервер | `fastapi.testclient.TestClient` вызывает приложение в процессе | фикстура `api` |
| Настоящее видео | синтетическое: `ffmpeg -f lavfi -i testsrc=duration=4:size=320x240:rate=30` → 120 кадров | фикстура `test_video` |
| Запрос воркера к backend | `httpx.post` подменён функцией, которая проверяет URL и файл | `test_result_upload.py` |

Следствие: тесты не проверяют специфику PostgreSQL (типы UUID, блокировки при `claim`, миграции Alembic).

## Файлы

### `tests/test_processing_service.py` — очередь задач на уровне сервиса (без HTTP)
Вызывает функции `backend/services/processing_service.py` напрямую.
- `test_processing_job_failure_and_retry`: pending → claim → failed → retry → снова pending.
- `test_cannot_retry_completed_job`: завершённую задачу нельзя перезапустить.
- `test_cannot_fail_pending_job`: нельзя пометить failed задачу, которую никто не взял.
- `test_retry_nonexistent_job`: retry несуществующей задачи → ошибка.

### `tests/test_processing_api.py` — HTTP API статуса и результата задачи
- `GET /processing-jobs/{id}`: существующая завершённая задача и несуществующая (404).
- `GET /processing-jobs/{id}/result`: скачивание после завершения; до завершения → 409; задача завершена, но файла нет → 404 «Result archive not found»; несуществующая задача → 404.

### `tests/test_result_upload.py` — воркер отправляет результат
- `test_upload_result`: `upload_result()` шлёт ZIP на `/processing-jobs/{id}/result` в поле `archive` и проверяет ответ (`raise_for_status`).

### `tests/test_video_upload.py` — загрузка видео и извлечение кадров
- `select_frame_indices` (выбор номеров кадров): номера уникальны и распределены равномерно (параметризация: 120/10, 120/120, 1000/300, 2001/2000, 37/10); не больше, чем кадров в видео.
- `POST /projects/{id}/video`:
  - извлекается ровно `frame_count` кадров; если просят больше, чем есть, берутся все; по умолчанию 300 (ограничено длиной тестового видео); максимум 2000;
  - извлечённые кадры совпадают с выбранными номерами: для 3 кадров эталон декодируется отдельным вызовом `ffmpeg -vf select=eq(n,…)`, пиксели сравниваются побайтно;
  - не видео / картинка без видеопотока → 400; `frame_count` вне диапазона (0, 9, 2001, 5000) → 422; слишком большой файл (лимит в тесте подменён на 1000 байт) → 413, и файл удаляется;
  - неизвестный проект → 404;
  - откат (`test_ffmpeg_failure_rolls_back`, несмотря на имя, ломает **базу данных** после извлечения): статус `failed`, текст ошибки сохранён, в `input/` пусто, записей `ProjectImage` нет;
  - кадры попадают в ZIP `GET /projects/{id}/input`.
- `GET /projects/{id}/videos/{vid}` и `/frames`: статус и список кадров, 404 для неизвестных видео и проекта.
- `GET .../frames/{filename}`: файл отдаётся; **защита от выхода из папки** (path traversal): `../`, URL-кодирование `%2E%2E`, `\`, абсолютный путь, имена не из списка кадров → отказ.
- `GET /ui/`: страница отдаётся (HTML, есть кнопка «Запустить обработку»). Логика страницы не тестируется.

## Что НЕ покрыто тестами (известные пробелы)

| Часть | Почему важно |
|---|---|
| `POST /projects`, `POST /projects/{id}/images` | основной путь загрузки снимков |
| HTTP-эндпоинты `process`, `claim`, `complete`, `fail`, `retry`, `POST result` | логика покрыта на уровне сервиса, маршруты и коды ответов — нет |
| `backend/worker/worker.py` кроме `upload_result` (claim, download, extract, основной цикл) | воркер проверялся только ручным прогоном end-to-end |
| `backend/worker/pipeline.py` (`run_colmap`) | COLMAP локально не установлен; проверялся ручным запуском вне этой машины |
| `backend/project_manager.py`, `scripts/upload_dataset.py` | — |
| Миграции Alembic, работа с настоящей PostgreSQL | тесты используют SQLite и `create_all` |
| `frontend/index.html` (JS) | только проверка, что страница отдаётся |
