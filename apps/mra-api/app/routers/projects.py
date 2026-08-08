import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_workspace_service, require_admin, require_csrf, require_editor, require_viewer
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.workspace_service import (
    ProjectNotFoundError,
    WorkspaceInUseError,
    WorkspacePersistenceError,
    WorkspaceService,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"], dependencies=[Depends(require_viewer)])


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Progetto non trovato.",
    )


def _persistence_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Impossibile salvare il progetto.",
    )


@router.get("", response_model=list[ProjectRead])
def list_projects(service: WorkspaceService = Depends(get_workspace_service)):
    return service.list_projects()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_editor), Depends(require_csrf)])
def create_project(
    payload: ProjectCreate,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.create_project(payload)
    except WorkspacePersistenceError as exc:
        raise _persistence_error(exc) from exc


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.get_project(project_id)
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc


@router.put("/{project_id}", response_model=ProjectRead, dependencies=[Depends(require_editor), Depends(require_csrf)])
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.update_project(project_id, payload)
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except WorkspacePersistenceError as exc:
        raise _persistence_error(exc) from exc


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin), Depends(require_csrf)])
def delete_project(
    project_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    try:
        service.delete_project(project_id)
    except ProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except WorkspaceInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Progetto utilizzato da un intervento.") from exc
    except WorkspacePersistenceError as exc:
        raise _persistence_error(exc) from exc
