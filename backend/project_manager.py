from pathlib import Path
from uuid import uuid4
import shutil
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = BASE_DIR / "storage" / "projects"

def create_project():
    print(PROJECTS_DIR)

    project_id = uuid4().hex[:8]
    print(project_id)

    project_path = PROJECTS_DIR / project_id
    print(project_path)
    project_path.mkdir()


    directories = ["input","analysis", "colmap", "gaussian", "result", "metrics","logs"]
    for directory in directories:
        project_path.joinpath(directory).mkdir()
        print(f"Created directory: {project_path.joinpath(directory)}")

    return project_id

def add_image(project_id, image):
    project_path = PROJECTS_DIR / project_id
    if not project_path.exists():
        raise ValueError(f"Project with ID {project_id} does not exist.")
    input_path = project_path / "input"

    extension = Path(image.filename).suffix
    if extension.lower() not in [".jpg", ".jpeg", ".png"]:
        raise ValueError(f"Unsupported file type: {extension}. "
                         f"Only .jpg, .jpeg, and .png are allowed.")
    try:
        Image.open(image.file).verify()
        Image.file.seek(0)
    except Exception:
        raise ValueError(f"File {image.filename} is not a valid image.")

    destination_path = input_path / image.filename

    with open (destination_path, "wb") as file:
        file.write(image.file.read())
    return destination_path

