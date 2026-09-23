from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from typing import Annotated
from sqlalchemy.orm import Session
from uuid import UUID
from backend.project_manager import (
    add_image,
    validate_image,
    create_project_directory,
    get_project_directory,
)
from backend.database.database import get_db
from backend.services.project_service import (
    create_project, 
    get_project,
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
            raise HTTPException(status_code=400, detail=str(e))

    paths = []
    for image in images:
        path = add_image(project_id, image)
        paths.append(path)

    return {
        "filenames": [image.filename for image in images],
        "Saved to": [str(path) for path in paths]
    }

