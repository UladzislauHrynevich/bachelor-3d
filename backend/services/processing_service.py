from uuid import UUID 
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pathlib import Path
import shutil
from fastapi import UploadFile

from backend.project_manager import get_project_directory
from backend.database.models import ProcessingJob

def create_processing_job(
        db: Session,
        project_id: UUID,
        provider: str = "Google_colab"
):
    job = ProcessingJob(
        project_id=project_id,
        status="pending",
        provider= provider
    )
    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        raise

    return job

def get_next_pending_job(db: Session) -> ProcessingJob | None:
    return(
        db.query(ProcessingJob)
        .filter(ProcessingJob.status == "pending")
        .order_by(ProcessingJob.created_at.asc())
        .first()
    )

def claim_next_pending_job(db: Session) -> ProcessingJob | None:
    job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.status == "pending")
        .order_by(ProcessingJob.created_at.asc())
        .first()
    )

    if job is None:
        return None

    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        raise

    return job

def complete_processing_job(
    db: Session,
    job_id: UUID
) -> ProcessingJob | None:
    job = db.get(ProcessingJob, job_id)

    if job is None:
        return None

    job.status = "completed"
    job.finished_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        raise

    return job

def fail_processing_job(
        db: Session,
        job_id: UUID,
) -> ProcessingJob | None:
    job = db.get(ProcessingJob, job_id)

    if job is None:
        return None
    if job.status != "processing":
        raise ValueError(
            "Only processing job can be marked as failed"
        )
    job.status = "failed"
    job.finished_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        raise

    return job

    
def retry_processing_job(
    db: Session,
    job_id: UUID
) -> ProcessingJob | None:
    job = db.get(ProcessingJob, job_id)

    if job is None:
        return None

    if job.status != "failed":
        raise ValueError(
            "Only failed jobs can be retried"
        )

    job.status = "pending"
    job.started_at = None
    job.finished_at = None

    try:
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        raise

    return job


def save_processing_result(
    db: Session,
    job_id: UUID,
    archive: UploadFile,
) -> Path:
    job = db.get(ProcessingJob, job_id)

    if job is None:
        raise ValueError(
            f"Processing job {job_id} not found"
        )

    if job.status != "processing":
        raise ValueError(
            "Only processing jobs can upload results"
        )

    project_directory = get_project_directory(job.project_id)
    result_directory = project_directory / "result" / str(job.id)

    result_directory.mkdir(parents=True, exist_ok=True)

    archive_path = result_directory / "result.zip"

    if archive_path.exists():
        raise ValueError("Result already uploaded")

    try:
        with archive_path.open("xb") as f:
            shutil.copyfileobj(archive.file, f)
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise

    return archive_path
