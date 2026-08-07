import uuid
from collections.abc import Sequence
from typing import Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Environment, MraObject, Project

WorkspaceEntity = TypeVar("WorkspaceEntity", Project, Environment, MraObject)


class WorkspaceRepositoryProtocol(Protocol):
    def list_projects(self) -> Sequence[Project]: ...
    def get_project(self, project_id: uuid.UUID) -> Project | None: ...
    def list_environments(self, project_id: uuid.UUID) -> Sequence[Environment]: ...
    def get_environment(self, environment_id: uuid.UUID) -> Environment | None: ...
    def list_objects(self, environment_id: uuid.UUID) -> Sequence[MraObject]: ...
    def get_object(self, object_id: uuid.UUID) -> MraObject | None: ...
    def add(self, entity: WorkspaceEntity) -> WorkspaceEntity: ...
    def save(self, entity: WorkspaceEntity) -> WorkspaceEntity: ...
    def delete(self, entity: WorkspaceEntity) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class SqlAlchemyWorkspaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_projects(self) -> Sequence[Project]:
        statement = select(Project).order_by(Project.updated_at.desc())
        return tuple(self.db.scalars(statement).all())

    def get_project(self, project_id: uuid.UUID) -> Project | None:
        return self.db.get(Project, project_id)

    def list_environments(self, project_id: uuid.UUID) -> Sequence[Environment]:
        statement = (
            select(Environment)
            .where(Environment.project_id == project_id)
            .order_by(Environment.created_at.asc())
        )
        return tuple(self.db.scalars(statement).all())

    def get_environment(self, environment_id: uuid.UUID) -> Environment | None:
        return self.db.get(Environment, environment_id)

    def list_objects(self, environment_id: uuid.UUID) -> Sequence[MraObject]:
        statement = (
            select(MraObject)
            .where(MraObject.environment_id == environment_id)
            .order_by(MraObject.name.asc())
        )
        return tuple(self.db.scalars(statement).all())

    def get_object(self, object_id: uuid.UUID) -> MraObject | None:
        return self.db.get(MraObject, object_id)

    def add(self, entity: WorkspaceEntity) -> WorkspaceEntity:
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def save(self, entity: WorkspaceEntity) -> WorkspaceEntity:
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: WorkspaceEntity) -> None:
        self.db.delete(entity)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
