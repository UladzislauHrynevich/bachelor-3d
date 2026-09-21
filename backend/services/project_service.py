from sqlalchemy.orm import Session

from backend.database.models import Project

def create_project(db: Session):
    project = Project()
    db.add(project)
    db.commit()
    db.refresh(project)



