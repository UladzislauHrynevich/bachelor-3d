from fastapi import FastAPI, UploadFile, File
from backend.project_manager import create_project, add_image

app = FastAPI()
@app.post("/projects")
def new_project():
    project_id = create_project()
    return {"project_id": project_id}

@app.post("/projects/{project_id}/images")
def upload_image(project_id: str, image: UploadFile):
    path = add_image(project_id, image)

    return {
        "filename": image.filename,
        "Saved to": str(path)
        }
