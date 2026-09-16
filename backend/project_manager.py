from pathlib import Path
from uuid import uuid4
import shutil

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

    return project_id, project_path