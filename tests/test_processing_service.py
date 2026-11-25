
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.database.database import Base
from backend.database.models import Project
from backend.services.processing_service import (
    create_processing_job,
    claim_next_pending_job,
    fail_processing_job,
    retry_processing_job,
    complete_processing_job,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()


def test_processing_job_failure_and_retry(db):
    project = Project()
    db.add(project)
    db.commit()
    db.refresh(project)

    job = create_processing_job(
        db=db,
        project_id=project.id,
    )

    assert job.status == "pending"

    claimed = claim_next_pending_job(db)

    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "processing"
    assert claimed.started_at is not None

    failed = fail_processing_job(db, job.id)

    assert failed is not None
    assert failed.status == "failed"
    assert failed.finished_at is not None

    retried = retry_processing_job(db, job.id)

    assert retried is not None
    assert retried.status == "pending"
    assert retried.started_at is None
    assert retried.finished_at is None

    claimed_again = claim_next_pending_job(db)

    assert claimed_again is not None
    assert claimed_again.id == job.id
    assert claimed_again.status == "processing"

    completed = complete_processing_job(db, job.id)

    assert completed is not None
    assert completed.status == "completed"
    assert completed.finished_at is not None



def test_cannot_retry_completed_job(db):
    project = Project()
    db.add(project)
    db.commit()
    db.refresh(project)

    job = create_processing_job(db, project.id)
    claim_next_pending_job(db)
    complete_processing_job(db, job.id)

    with pytest.raises(ValueError):
        retry_processing_job(db, job.id)


def test_cannot_fail_pending_job(db):
    project = Project()
    db.add(project)
    db.commit()
    db.refresh(project)

    job = create_processing_job(db, project.id)

    with pytest.raises(ValueError):
        fail_processing_job(db, job.id)


def test_retry_nonexistent_job(db):
    result = retry_processing_job(db, uuid4())
    assert result is None
