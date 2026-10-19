from pathlib import Path
import shutil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.project_manager import get_project_directory, validate_image
from backend.services.project_service import create_project, get_project
from backend.services.image_service import create_image

router = APIRouter()

@router.post("/projects")
def new_project(db: Session = Depends(get_db)):
    project = create_project(db)
    return {
        "project_id": project.id
    }


@router.post("/projects/{project_id}/images")
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


@router.get("/projects/{project_id}/input")
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

