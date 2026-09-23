from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Annotated

from backend.database.database import get_db
from backend.project_manager import add_image
from backend.services.project_service import create_project 

app = FastAPI()
@app.post("/projects")
def new_project(db: Session = Depends(get_db)):
    project= create_project(db)
    return {"project_id": project.id}

@app.post("/projects/{project_id}/images")
def upload_images(project_id: str, images: Annotated[list[UploadFile], File()]):
    try:
        paths = []
        for image in images:
            path = add_image(project_id, image)
            paths.append(path)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "filenames": [image.filename for image in images],
        "Saved to": [str(path) for path in paths]
        }
