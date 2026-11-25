from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import ProcessingJob
from backend.project_manager import get_project_directory
from backend.services.project_service import get_project
from backend.services.processing_service import (
    create_processing_job,
    claim_next_pending_job,
    complete_processing_job,
    fail_processing_job,
    retry_processing_job,
    save_processing_result,
)

router = APIRouter()

@router.post("/projects/{project_id}/process")
def process_project(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    project = get_project(db, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} not found"
        )

    if len(project.images) == 0:
        raise HTTPException(
            status_code=400,
            detail="Project has no images"
        )

    job = create_processing_job(
        db=db,
        project_id=project_id
    )

    return {
        "job_id": str(job.id),
        "project_id": str(job.project_id),
        "status": job.status,
        "provider": job.provider,
        "created_at": job.created_at
    }


@router.post("/processing-jobs/claim")
def claim_processing_job(
    db: Session = Depends(get_db)
):
    job = claim_next_pending_job(db)

    if job is None:
        return {"job": None}

    return {
        "job": {
            "id": str(job.id),
            "project_id": str(job.project_id),
            "status": job.status,
            "provider": job.provider,
            "created_at": job.created_at,
            "started_at": job.started_at
        }
    }


@router.post("/processing-jobs/{job_id}/complete")
def complete_job(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    job = complete_processing_job(db, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Processing job {job_id} not found"
        )

    return {
        "job_id": str(job.id),
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at
    }


@router.post("/processing-jobs/{job_id}/fail")
def fail_job(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    try:
        job = fail_processing_job(db, job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Processing job {job_id} not found"
        )

    return {
        "job_id": str(job.id),
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at
    }


@router.post("/processing-jobs/{job_id}/retry")
def retry_job(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    try:
        job = retry_processing_job(db, job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Processing job {job_id} not found"
        )

    return {
        "job_id": str(job.id),
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at
    }


@router.post("/processing-jobs/{job_id}/result")
def upload_processing_result(
    job_id: UUID,
    archive: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not archive.filename or not archive.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP archives are supported"
        )

    try:
        archive_path = save_processing_result(
            db=db,
            job_id=job_id,
            archive=archive
        )
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    return {
        "job_id": str(job_id),
        "status": "uploaded",
        "filename": archive_path.name
    }


@router.get("/processing-jobs/{job_id}")
def get_processing_job(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    job = db.get(ProcessingJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Processing job not found",
        )

    return {
        "id": str(job.id),
        "project_id": str(job.project_id),
        "status": job.status,
        "provider": job.provider,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get("/processing-jobs/{job_id}/result")
def download_processing_result(
    job_id: UUID,
    db: Session = Depends(get_db),
):
    job = db.get(ProcessingJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Processing job not found",
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Processing job is not completed",
        )

    result_path = (
        get_project_directory(job.project_id)
        / "result"
        / str(job.id)
        / "result.zip"
    )

    if not result_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Result archive not found",
        )

    return FileResponse(
        path=result_path,
        filename="result.zip",
        media_type="application/zip",
    )

