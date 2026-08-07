import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_knowledge_revision_service, require_csrf, require_editor, require_viewer
from app.schemas import KnowledgeCardRead, KnowledgeRevisionRead
from app.services.knowledge_revision_service import (
    KnowledgeRevisionNotFoundError,
    KnowledgeRevisionPersistenceError,
    KnowledgeRevisionService,
)

router = APIRouter(
    prefix="/api/v1/knowledge-cards",
    tags=["knowledge-revisions"],
    dependencies=[Depends(require_viewer)],
)


@router.get(
    "/{card_id}/revisions",
    response_model=list[KnowledgeRevisionRead],
)
def list_revisions(
    card_id: uuid.UUID,
    service: KnowledgeRevisionService = Depends(get_knowledge_revision_service),
):
    try:
        return service.list_revisions(card_id)
    except KnowledgeRevisionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge Card non trovata.",
        ) from exc


@router.post(
    "/{card_id}/revisions/{revision_id}/restore",
    response_model=KnowledgeCardRead,
    dependencies=[Depends(require_editor), Depends(require_csrf)],
)
def restore_revision(
    card_id: uuid.UUID,
    revision_id: uuid.UUID,
    service: KnowledgeRevisionService = Depends(get_knowledge_revision_service),
):
    try:
        return service.restore(card_id, revision_id)
    except KnowledgeRevisionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revisione o Knowledge Card non trovata.",
        ) from exc
    except KnowledgeRevisionPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile ripristinare la revisione.",
        ) from exc
