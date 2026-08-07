import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_workspace_service
from app.schemas import MraObjectCreate, MraObjectRead, MraObjectUpdate
from app.services.workspace_service import (
    EnvironmentNotFoundError,
    MraObjectNotFoundError,
    WorkspacePersistenceError,
    WorkspaceService,
)

router = APIRouter(prefix="/api/v1", tags=["objects"])


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _persistence_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Impossibile salvare l'oggetto.",
    )


@router.get("/environments/{environment_id}/objects", response_model=list[MraObjectRead])
def list_objects(
    environment_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.list_objects(environment_id)
    except EnvironmentNotFoundError as exc:
        raise _not_found("Ambiente non trovato.") from exc


@router.post(
    "/environments/{environment_id}/objects",
    response_model=MraObjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_object(
    environment_id: uuid.UUID,
    payload: MraObjectCreate,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.create_object(environment_id, payload)
    except EnvironmentNotFoundError as exc:
        raise _not_found("Ambiente non trovato.") from exc
    except WorkspacePersistenceError as exc:
        raise _persistence_error() from exc


@router.get("/objects/{object_id}", response_model=MraObjectRead)
def get_object(
    object_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.get_object(object_id)
    except MraObjectNotFoundError as exc:
        raise _not_found("Oggetto non trovato.") from exc


@router.put("/objects/{object_id}", response_model=MraObjectRead)
def update_object(
    object_id: uuid.UUID,
    payload: MraObjectUpdate,
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return service.update_object(object_id, payload)
    except MraObjectNotFoundError as exc:
        raise _not_found("Oggetto non trovato.") from exc
    except WorkspacePersistenceError as exc:
        raise _persistence_error() from exc


@router.delete("/objects/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(
    object_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    try:
        service.delete_object(object_id)
    except MraObjectNotFoundError as exc:
        raise _not_found("Oggetto non trovato.") from exc
    except WorkspacePersistenceError as exc:
        raise _persistence_error() from exc
