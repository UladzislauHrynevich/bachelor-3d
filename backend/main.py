from fastapi import FastAPI, UploadFile, File, HTTPException
from project_manager import create_project, add_image, validate_image, get_project_path
from typing import Annotated

app = FastAPI()
@app.post("/projects")
def new_project():
    project_id = create_project()
    project_path = get_project_path(project_id)
    return {"project_id": project_id, "project_path": project_path}



@app.post("/projects/{project_id}/images")

def upload_images(project_id: str, images: Annotated[list[UploadFile], File()]):

    for image in images:
        try:
            validate_image(image)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

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

