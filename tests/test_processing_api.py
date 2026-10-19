
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import backend.main as main
from backend.database.database import Base, get_db
from backend.database.models import Project
from backend.services.processing_service import (
    create_processing_job,
    claim_next_pending_job,
    complete_processing_job,
)
import backend.routers.processing as processing_router


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    main.app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
          processing_router,
          "get_project_directory",
          lambda project_id: tmp_path / str(project_id),
      )
  
    try:
        with TestClient(main.app) as client:
            yield client, engine, tmp_path
    finally:
        main.app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def create_job(engine, completed=False):
    with Session(engine) as db:
        project = Project()
        db.add(project)
        db.commit()
        db.refresh(project)

        job = create_processing_job(db, project.id)

        if completed:
            claim_next_pending_job(db)
            complete_processing_job(db, job.id)

        return str(job.id), str(project.id)


def test_get_completed_job(api):
    client, engine, _ = api
    job_id, project_id = create_job(engine, completed=True)

    response = client.get(f"/processing-jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert response.json()["project_id"] == project_id
    assert response.json()["status"] == "completed"
    assert response.json()["finished_at"] is not None


def test_get_nonexistent_job(api):
    client, _, _ = api

    response = client.get(f"/processing-jobs/{uuid4()}")

    assert response.status_code == 404


def test_download_completed_result(api):
    client, engine, tmp_path = api
    job_id, project_id = create_job(engine, completed=True)

    result_directory = (
        tmp_path / project_id / "result" / job_id
    )
    result_directory.mkdir(parents=True)

    archive_path = result_directory / "result.zip"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr("metadata.json", '{"pipeline": "test"}')

    response = client.get(
        f"/processing-jobs/{job_id}/result"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    with ZipFile(BytesIO(response.content)) as archive:
        assert "metadata.json" in archive.namelist()
        assert archive.read("metadata.json") == b'{"pipeline": "test"}'


def test_download_result_before_completion(api):
    client, engine, _ = api
    job_id, _ = create_job(engine)

    response = client.get(
        f"/processing-jobs/{job_id}/result"
    )

    assert response.status_code == 409


def test_download_missing_result(api):
    client, engine, _ = api
    job_id, _ = create_job(engine, completed=True)

    response = client.get(
        f"/processing-jobs/{job_id}/result"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Result archive not found"


def test_download_nonexistent_job(api):
    client, _, _ = api

    response = client.get(
        f"/processing-jobs/{uuid4()}/result"
    )

    assert response.status_code == 404
