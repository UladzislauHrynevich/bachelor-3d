from pathlib import Path
from uuid import uuid4
import shutil
from project_manager import create_project
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = BASE_DIR / "storage" / "projects"


project_id= create_project()

test_image = BASE_DIR / "test.jpg"

