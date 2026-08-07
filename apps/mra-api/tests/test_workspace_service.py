import uuid

import pytest

from app.models import Project
from app.schemas import ProjectCreate
from app.services.workspace_service import WorkspacePersistenceError, WorkspaceService


class FailingWorkspaceRepository:
    def __init__(self) -> None:
        self.rollback_called = False

    def add(self, entity):
        raise RuntimeError("unexpected database failure")

    def rollback(self) -> None:
        self.rollback_called = True


def test_unexpected_persistence_error_rolls_back():
    repository = FailingWorkspaceRepository()
    service = WorkspaceService(repository)

    with pytest.raises(WorkspacePersistenceError):
        service.create_project(
            ProjectCreate(name="Officina", project_type="Workshop")
        )

    assert repository.rollback_called is True


def test_project_model_uses_uuid_identifiers():
    project = Project(name="Officina", project_type="Workshop")
    project.id = uuid.uuid4()
    assert isinstance(project.id, uuid.UUID)
