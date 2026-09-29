from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from typing import Annotated
from sqlalchemy.orm import Session
from uuid import UUID

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