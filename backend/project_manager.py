from pathlib import Path
from PIL import Image
import shutil
from uuid import uuid4

from backend.database.models import Project

#its should be like a manger of files
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = BASE_DIR / "storage" / "projects"

def create_project_directory(project_id):
    project_directory = get_project_directory(project_id)
    project_directory.mkdir()

    directories = [ 
    "input",
    "analysis", 
    "colmap",
    "gaussian",
    "result", 
    "metrics",
    "logs"
    ]
    
    for directory in directories:
        project_directory.joinpath(directory).mkdir()

    return project_directory

def delete_project_directory(project_directory):
    shutil.rmtree(project_directory)
    return project_directory

def get_project_directory(project_id):
    return PROJECTS_DIR / str(project_id)
 

def add_image(project_id, image):
    extension = Path(image.filename).suffix.lower()
    storage_name =  uuid4().hex + extension
    destination_path = get_project_directory(project_id) / "input" / storage_name

    with open (destination_path, "wb") as file:
        file.write(image.file.read())
        
    return destination_path

def validate_image(image):
    extension = Path(image.filename).suffix
    if extension.lower() not in [".jpg", ".jpeg", ".png"]:
        raise ValueError(f"Unsupported file type: {extension}. "
                         f"Only .jpg, .jpeg, and .png are allowed.")
    try:
        Image.open(image.file).verify()
        image.file.seek(0)
    except Exception:
        raise ValueError(f"File {image.filename} is not a valid image.")

