from typing import Annotated
from uuid import UUID, uuid4

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile,
)
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.services.project_service import get_project
from backend.services import video_service
from backend.services.video_service import (
    DEFAULT_FRAME_COUNT,
    MAX_FRAME_COUNT,
    MIN_FRAME_COUNT,
    InvalidVideoError,
    VideoTooLargeError,
)

router = APIRouter()


def _require_project(db: Session, project_id: UUID):
    if get_project(db, project_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} not found"
        )


@router.post("/projects/{project_id}/video")
def upload_video(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    video: Annotated[UploadFile, File()],
    frame_count: Annotated[
        int, Form(ge=MIN_FRAME_COUNT, le=MAX_FRAME_COUNT)
    ] = DEFAULT_FRAME_COUNT,
    db: Session = Depends(get_db),
):
    _require_project(db, project_id)

    video_id = uuid4()

    try:
        metadata = video_service.register_video(
            project_id, video_id, video, frame_count
        )
    except VideoTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error))
    except InvalidVideoError as error:
        raise HTTPException(status_code=400, detail=str(error))

    # resolved at call time so tests can monkeypatch it
    background_tasks.add_task(video_service.extract_frames, project_id, video_id)

    return {
        "video_id": str(video_id),
        "status": metadata["status"],
    }


@router.get("/projects/{project_id}/videos/{video_id}")
def get_video(
    project_id: UUID,
    video_id: UUID,
    db: Session = Depends(get_db),
):
    _require_project(db, project_id)

    metadata = video_service.read_video_metadata(project_id, video_id)
    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail=f"Video {video_id} not found"
        )
    return metadata
