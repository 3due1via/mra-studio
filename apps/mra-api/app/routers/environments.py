import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_workspace_service, require_admin, require_csrf, require_editor, require_viewer
from app.schemas import EnvironmentCreate, EnvironmentRead, EnvironmentUpdate
from app.services.workspace_service import (
    EnvironmentNotFoundError,
    ProjectNotFoundError,
    WorkspacePersistenceError,
    WorkspaceService,
)

router = APIRouter(prefix="/api/v1", tags=["environments"], dependencies=[Depends(require_viewer)])


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _persistence_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Impossibile salvare l'ambiente.",
    )


@router.get("/projects/{project_id}/environments", response_model=list[EnvironmentRead])
def list_environments(
    project_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.list_environments(project_id)
    except ProjectNotFoundError as exc:
        raise _not_found("Progetto non trovato.") from exc


@router.post(
    "/projects/{project_id}/environments",
    response_model=EnvironmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_editor), Depends(require_csrf)],
)
def create_environment(
    project_id: uuid.UUID,
    payload: EnvironmentCreate,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.create_environment(project_id, payload)
    except ProjectNotFoundError as exc:
        raise _not_found("Progetto non trovato.") from exc
    except WorkspacePersistenceError as exc:
        raise _persistence_error() from exc


@router.get("/environments/{environment_id}", response_model=EnvironmentRead)
def get_environment(
    environment_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.get_environment(environment_id)
    except EnvironmentNotFoundError as exc:
        raise _not_found("Ambiente non trovato.") from exc


@router.put("/environments/{environment_id}", response_model=EnvironmentRead, dependencies=[Depends(require_editor), Depends(require_csrf)])
def update_environment(
    environment_id: uuid.UUID,
    payload: EnvironmentUpdate,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.update_environment(environment_id, payload)
    except EnvironmentNotFoundError as exc:
        raise _not_found("Ambiente non trovato.") from exc
    except WorkspacePersistenceError as exc:
        raise _persistence_error() from exc


@router.delete("/environments/{environment_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin), Depends(require_csrf)])
def delete_environment(
    environment_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    try:
        service.delete_environment(environment_id)
    except EnvironmentNotFoundError as exc:
        raise _not_found("Ambiente non trovato.") from exc
    except WorkspacePersistenceError as exc:
        raise _persistence_error() from exc
