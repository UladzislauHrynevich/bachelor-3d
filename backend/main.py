from fastapi import FastAPI, UploadFile, File
from backend.project_manager import create_project, add_image
from typing import Annotated

app = FastAPI()
@app.post("/projects")
def new_project():
    project_id = create_project()
    return {"project_id": project_id}

@app.post("/projects/{project_id}/images")
def upload_images(project_id: str, images: Annotated[list[UploadFile], File()]):
    paths = []
    for image in images:
        path = add_image(project_id, image)
        paths.append(path)

    return {
        "filenames": [image.filename for image in images],
        "Saved to": [str(path) for path in paths]
        }
