from sqlalchemy.orm import Session

from backend.database.models import Project

from backend.project_manager import create_project_directory

def create_project(db: Session):   #add project to db >> commit all >> refresh project
    project = Project()

    db.add(project)
    db.flush()

    create_project_directory(project)

    db.commit()
    db.refresh(project)

    return project


