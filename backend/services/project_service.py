from sqlalchemy.orm import Session
from uuid import UUID
from backend.database.models import Project
from backend.project_manager import (
    create_project_directory,
    delete_project_directory,
)

def create_project(db: Session):   #add project to db >> commit all >> refresh project
    project = Project()
    project_directory = None

    try:
        db.add(project)
        db.flush()
        project_directory = create_project_directory(project)
        db.commit()
        db.refresh(project)
    except:
        db.rollback()
        if project_directory is not None:
            delete_project_directory(project_directory)
        raise
    

    return project

def get_project(db: Session, project_id: UUID):
    return db.get(Project, project_id)


