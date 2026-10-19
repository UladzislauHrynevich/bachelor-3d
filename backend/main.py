from backend.routers.processing import router as processing_router
from backend.routers.projects import router as projects_router
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from backend.project_manager import get_project_directory

from typing import Annotated
from sqlalchemy.orm import Session
from uuid import UUID
import shutil
from pathlib import Path



from backend.database.models import ProcessingJob

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
from backend.services.processing_service import (
    create_processing_job,
    claim_next_pending_job,
    complete_processing_job,
    fail_processing_job,
    retry_processing_job,
    save_processing_result,
)

app = FastAPI()



















app.include_router(projects_router)

app.include_router(processing_router)
