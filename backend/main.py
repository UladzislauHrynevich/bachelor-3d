from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse

from typing import Annotated
from sqlalchemy.orm import Session
from uuid import UUID
import shutil
from pathlib import Path

from backend.project_manager import (
    validate_image,
    create_project_directory,
    get_project_directory,
)
from backend.database.database import get_db
from backend.services.project_service import (
    create_project, 
    get_project,
)
from backend.services.image_service import create_image
from backend.services.processing_service import (
    create_processing_job,
    claim_next_pending_job,
    complete_processing_job,
)

app = FastAPI()
@app.post("/projects")
def new_project(db: Session = Depends(get_db)):
    project = create_project(db)
    return {
        "project_id": project.id
    }




@app.post("/projects/{project_id}/images")
def upload_images(
    project_id: UUID,
    images: Annotated[list[UploadFile], File()],
    db: Session = Depends(get_db)
):
    project = get_project(db, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} not found"
        )

   
    for image in images:
        try:
            validate_image(image)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )

    saved_images = []

    for image in images:
        db_image = create_image(db, project_id, image)
        saved_images.append(db_image)

    return {
        "images": [
            {
                "id": str(image.id),
                "original_name": image.original_name,
                "storage_path": image.storage_path,
                "size_bytes": image.size_bytes
            }
            for image in saved_images
        ]
    }

@app.post("/projects/{project_id}/process")
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

@app.post("/processing-jobs/claim")
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

@app.get("/projects/{project_id}/input")
def download_project_input(
    project_id: UUID,
    db: Session = Depends(get_db)
):
    project = get_project(db, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} not found"
        )

    input_directory = get_project_directory(project_id) / "input"

    if not input_directory.exists():
        raise HTTPException(
            status_code=404,
            detail="Project input directory not found"
        )

    archive_base = Path("/tmp") / f"{project_id}_input"

    zip_path = shutil.make_archive(
        str(archive_base),
        "zip",
        input_directory
    )

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{project_id}_input.zip"
    )

@app.post("/processing-jobs/{job_id}/complete")
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