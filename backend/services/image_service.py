from uuid import UUID

from sqlalchemy.orm import Session

from backend.database.models import ProjectImage
from backend.project_manager import add_image


def create_image(db: Session, project_id: UUID, image):
    path = add_image(project_id, image)

    try:
        db_image = ProjectImage(
            project_id=project_id,
            original_name=image.filename,
            storage_path=str(path),
            size_bytes=path.stat().st_size
        )

        db.add(db_image)
        db.commit()
        db.refresh(db_image)

    except Exception:
        db.rollback()

        if path.exists():
            path.unlink()

        raise

    return db_image