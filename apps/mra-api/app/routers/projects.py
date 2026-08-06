import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Environment, MraObject, Project
from app.schemas import (
    EnvironmentCreate,
    EnvironmentRead,
    MraObjectCreate,
    MraObjectRead,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Progetto non trovato.")
    return project


def _environment_or_404(db: Session, environment_id: uuid.UUID) -> Environment:
    environment = db.get(Environment, environment_id)
    if environment is None:
        raise HTTPException(status_code=404, detail="Ambiente non trovato.")
    return environment


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    statement = select(Project).order_by(Project.updated_at.desc())
    return list(db.scalars(statement).all())


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    return _project_or_404(db, project_id)


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
):
    project = _project_or_404(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    project = _project_or_404(db, project_id)
    db.delete(project)
    db.commit()


@router.get("/{project_id}/environments", response_model=list[EnvironmentRead])
def list_environments(project_id: uuid.UUID, db: Session = Depends(get_db)):
    _project_or_404(db, project_id)
    statement = (
        select(Environment)
        .where(Environment.project_id == project_id)
        .order_by(Environment.created_at.asc())
    )
    return list(db.scalars(statement).all())


@router.post(
    "/{project_id}/environments",
    response_model=EnvironmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_environment(
    project_id: uuid.UUID,
    payload: EnvironmentCreate,
    db: Session = Depends(get_db),
):
    _project_or_404(db, project_id)
    environment = Environment(project_id=project_id, **payload.model_dump())
    db.add(environment)
    db.commit()
    db.refresh(environment)
    return environment


@router.get(
    "/environments/{environment_id}/objects",
    response_model=list[MraObjectRead],
)
def list_objects(environment_id: uuid.UUID, db: Session = Depends(get_db)):
    _environment_or_404(db, environment_id)
    statement = (
        select(MraObject)
        .where(MraObject.environment_id == environment_id)
        .order_by(MraObject.name.asc())
    )
    return list(db.scalars(statement).all())


@router.post(
    "/environments/{environment_id}/objects",
    response_model=MraObjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_object(
    environment_id: uuid.UUID,
    payload: MraObjectCreate,
    db: Session = Depends(get_db),
):
    _environment_or_404(db, environment_id)
    item = MraObject(environment_id=environment_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
