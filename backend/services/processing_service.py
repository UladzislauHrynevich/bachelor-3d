from uuid import UUID 
from sqlalchemy.orm import Session
from datetime import datetime, timezone

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