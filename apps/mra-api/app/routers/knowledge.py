import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_knowledge_service, require_admin, require_csrf, require_editor, require_viewer
from app.schemas import (
    KnowledgeCardCreate,
    KnowledgeCardRead,
    KnowledgeCardUpdate,
)
from app.services.knowledge_service import (
    KnowledgeCardCodeConflictError,
    KnowledgeCardNotFoundError,
    KnowledgeCardInUseError,
    KnowledgePersistenceError,
    KnowledgeService,
)

router = APIRouter(
    prefix="/api/v1/knowledge-cards",
    tags=["knowledge"],
    dependencies=[Depends(require_viewer)],
)


@router.get("", response_model=list[KnowledgeCardRead])
def list_cards(
    search: str | None = Query(default=None),
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    service: KnowledgeService = Depends(
        get_knowledge_service
    ),
):
    return service.list_cards(
        search=search,
        status_filter=status_filter,
    )


@router.post(
    "",
    response_model=KnowledgeCardRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_editor), Depends(require_csrf)],
)
def create_card(
    payload: KnowledgeCardCreate,
    service: KnowledgeService = Depends(
        get_knowledge_service
    ),
):
    try:
        return service.create_card(payload)
    except KnowledgeCardCodeConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Esiste già una Knowledge Card "
                "con questo codice."
            ),
        ) from exc
    except KnowledgePersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile salvare la Knowledge Card.",
        ) from exc


@router.get(
    "/{card_id}",
    response_model=KnowledgeCardRead,
)
def get_card(
    card_id: uuid.UUID,
    service: KnowledgeService = Depends(
        get_knowledge_service
    ),
):
    try:
        return service.get_card(card_id)
    except KnowledgeCardNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge Card non trovata.",
        ) from exc


@router.put(
    "/{card_id}",
    response_model=KnowledgeCardRead,
    dependencies=[Depends(require_editor), Depends(require_csrf)],
)
def update_card(
    card_id: uuid.UUID,
    payload: KnowledgeCardUpdate,
    service: KnowledgeService = Depends(
        get_knowledge_service
    ),
):
    try:
        return service.update_card(card_id, payload)
    except KnowledgeCardNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge Card non trovata.",
        ) from exc
    except KnowledgePersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile aggiornare la Knowledge Card.",
        ) from exc


@router.delete(
    "/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin), Depends(require_csrf)],
)
def delete_card(
    card_id: uuid.UUID,
    service: KnowledgeService = Depends(
        get_knowledge_service
    ),
) -> None:
    try:
        service.delete_card(card_id)
    except KnowledgeCardNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge Card non trovata.",
        ) from exc
    except KnowledgeCardInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Knowledge Card utilizzata da un intervento.") from exc
    except KnowledgePersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile eliminare la Knowledge Card.",
        ) from exc
