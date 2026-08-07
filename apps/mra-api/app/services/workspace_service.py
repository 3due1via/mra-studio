import uuid
from collections.abc import Sequence

from app.models import Environment, MraObject, Project
from app.repositories.workspace_repository import WorkspaceRepositoryProtocol
from app.schemas import (
    EnvironmentCreate,
    EnvironmentUpdate,
    MraObjectCreate,
    MraObjectUpdate,
    ProjectCreate,
    ProjectUpdate,
)


class ProjectNotFoundError(Exception):
    pass


class EnvironmentNotFoundError(Exception):
    pass


class MraObjectNotFoundError(Exception):
    pass


class WorkspacePersistenceError(Exception):
    pass


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepositoryProtocol) -> None:
        self.repository = repository

    def list_projects(self) -> Sequence[Project]:
        return self.repository.list_projects()

    def get_project(self, project_id: uuid.UUID) -> Project:
        project = self.repository.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError
        return project

    def create_project(self, payload: ProjectCreate) -> Project:
        return self._persist_add(Project(**payload.model_dump()))

    def update_project(self, project_id: uuid.UUID, payload: ProjectUpdate) -> Project:
        project = self.get_project(project_id)
        return self._persist_update(project, payload.model_dump(exclude_unset=True))

    def delete_project(self, project_id: uuid.UUID) -> None:
        self._persist_delete(self.get_project(project_id))

    def list_environments(self, project_id: uuid.UUID) -> Sequence[Environment]:
        self.get_project(project_id)
        return self.repository.list_environments(project_id)

    def get_environment(self, environment_id: uuid.UUID) -> Environment:
        environment = self.repository.get_environment(environment_id)
        if environment is None:
            raise EnvironmentNotFoundError
        return environment

    def create_environment(
        self, project_id: uuid.UUID, payload: EnvironmentCreate
    ) -> Environment:
        self.get_project(project_id)
        return self._persist_add(
            Environment(project_id=project_id, **payload.model_dump())
        )

    def update_environment(
        self, environment_id: uuid.UUID, payload: EnvironmentUpdate
    ) -> Environment:
        environment = self.get_environment(environment_id)
        return self._persist_update(
            environment, payload.model_dump(exclude_unset=True)
        )

    def delete_environment(self, environment_id: uuid.UUID) -> None:
        self._persist_delete(self.get_environment(environment_id))

    def list_objects(self, environment_id: uuid.UUID) -> Sequence[MraObject]:
        self.get_environment(environment_id)
        return self.repository.list_objects(environment_id)

    def get_object(self, object_id: uuid.UUID) -> MraObject:
        item = self.repository.get_object(object_id)
        if item is None:
            raise MraObjectNotFoundError
        return item

    def create_object(
        self, environment_id: uuid.UUID, payload: MraObjectCreate
    ) -> MraObject:
        self.get_environment(environment_id)
        return self._persist_add(
            MraObject(environment_id=environment_id, **payload.model_dump())
        )

    def update_object(
        self, object_id: uuid.UUID, payload: MraObjectUpdate
    ) -> MraObject:
        item = self.get_object(object_id)
        return self._persist_update(item, payload.model_dump(exclude_unset=True))

    def delete_object(self, object_id: uuid.UUID) -> None:
        self._persist_delete(self.get_object(object_id))

    def _persist_add(self, entity):
        try:
            created = self.repository.add(entity)
            self.repository.commit()
            return created
        except Exception as exc:
            self.repository.rollback()
            raise WorkspacePersistenceError from exc

    def _persist_update(self, entity, values: dict):
        for field, value in values.items():
            setattr(entity, field, value)
        try:
            saved = self.repository.save(entity)
            self.repository.commit()
            return saved
        except Exception as exc:
            self.repository.rollback()
            raise WorkspacePersistenceError from exc

    def _persist_delete(self, entity) -> None:
        try:
            self.repository.delete(entity)
            self.repository.commit()
        except Exception as exc:
            self.repository.rollback()
            raise WorkspacePersistenceError from exc
