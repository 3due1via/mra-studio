import uuid
from collections.abc import Sequence
from sqlalchemy.exc import IntegrityError

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
from app.services.audit_service import (
    AuditService, ENVIRONMENT_CREATED, ENVIRONMENT_DELETED, ENVIRONMENT_UPDATED,
    MRA_OBJECT_CREATED, MRA_OBJECT_DELETED, MRA_OBJECT_UPDATED,
    PROJECT_CREATED, PROJECT_DELETED, PROJECT_UPDATED,
)


class ProjectNotFoundError(Exception):
    pass


class EnvironmentNotFoundError(Exception):
    pass


class MraObjectNotFoundError(Exception):
    pass


class WorkspacePersistenceError(Exception):
    pass


class WorkspaceInUseError(Exception):
    pass


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepositoryProtocol, audit: AuditService | None = None) -> None:
        self.repository = repository
        self.audit = audit

    def list_projects(self) -> Sequence[Project]:
        return self.repository.list_projects()

    def get_project(self, project_id: uuid.UUID) -> Project:
        project = self.repository.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError
        return project

    def create_project(self, payload: ProjectCreate) -> Project:
        return self._persist_add(Project(**payload.model_dump()), PROJECT_CREATED, "project")

    def update_project(self, project_id: uuid.UUID, payload: ProjectUpdate) -> Project:
        project = self.get_project(project_id)
        return self._persist_update(project, payload.model_dump(exclude_unset=True), PROJECT_UPDATED, "project")

    def delete_project(self, project_id: uuid.UUID) -> None:
        self._persist_delete(self.get_project(project_id), PROJECT_DELETED, "project")

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
        return self._persist_add(Environment(project_id=project_id, **payload.model_dump()), ENVIRONMENT_CREATED, "environment")

    def update_environment(
        self, environment_id: uuid.UUID, payload: EnvironmentUpdate
    ) -> Environment:
        environment = self.get_environment(environment_id)
        return self._persist_update(environment, payload.model_dump(exclude_unset=True), ENVIRONMENT_UPDATED, "environment")

    def delete_environment(self, environment_id: uuid.UUID) -> None:
        self._persist_delete(self.get_environment(environment_id), ENVIRONMENT_DELETED, "environment")

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
        return self._persist_add(MraObject(environment_id=environment_id, **payload.model_dump()), MRA_OBJECT_CREATED, "mra_object")

    def update_object(
        self, object_id: uuid.UUID, payload: MraObjectUpdate
    ) -> MraObject:
        item = self.get_object(object_id)
        return self._persist_update(item, payload.model_dump(exclude_unset=True), MRA_OBJECT_UPDATED, "mra_object")

    def delete_object(self, object_id: uuid.UUID) -> None:
        self._persist_delete(self.get_object(object_id), MRA_OBJECT_DELETED, "mra_object")

    @staticmethod
    def _snapshot(entity) -> dict:
        if isinstance(entity, Project):
            fields = ("name", "project_type", "customer", "description", "status", "progress")
        elif isinstance(entity, Environment):
            fields = ("project_id", "name", "environment_type", "area_m2", "height_m", "width_m", "length_m", "notes")
        else:
            fields = ("environment_id", "category", "name", "brand", "model", "serial_number", "description", "status", "metadata_json")
        return {
            name: str(value) if isinstance((value := getattr(entity, name)), uuid.UUID) else value
            for name in fields
        }

    def _failure(self, entity_type: str, entity_id) -> None:
        if self.audit:
            self.audit.record_failure_after_rollback(entity_type=entity_type, entity_id=entity_id, code="persistence_error", commit=self.repository.commit, rollback=self.repository.rollback)

    def _persist_add(self, entity, action: str, entity_type: str):
        try:
            created = self.repository.add(entity)
            if self.audit:
                self.audit.record_change(action=action, entity_type=entity_type, entity_id=created.id, before=None, after=self._snapshot(created))
            self.repository.commit()
            return created
        except Exception as exc:
            self.repository.rollback()
            self._failure(entity_type, getattr(entity, "id", None))
            raise WorkspacePersistenceError from exc

    def _persist_update(self, entity, values: dict, action: str, entity_type: str):
        before = self._snapshot(entity)
        for field, value in values.items():
            setattr(entity, field, value)
        try:
            saved = self.repository.save(entity)
            if self.audit:
                self.audit.record_change(action=action, entity_type=entity_type, entity_id=saved.id, before=before, after=self._snapshot(saved))
            self.repository.commit()
            return saved
        except Exception as exc:
            self.repository.rollback()
            self._failure(entity_type, entity.id)
            raise WorkspacePersistenceError from exc

    def _persist_delete(self, entity, action: str, entity_type: str) -> None:
        before = self._snapshot(entity)
        try:
            self.repository.delete(entity)
            if self.audit:
                self.audit.record_change(action=action, entity_type=entity_type, entity_id=entity.id, before=before, after=None)
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if constraint in {"fk_interventions_project", "fk_interventions_environment", "fk_interventions_object", "fk_interventions_environment_project", "fk_interventions_object_environment"}:
                raise WorkspaceInUseError from exc
            self._failure(entity_type, entity.id)
            raise WorkspacePersistenceError from exc
        except Exception as exc:
            self.repository.rollback()
            self._failure(entity_type, entity.id)
            raise WorkspacePersistenceError from exc
