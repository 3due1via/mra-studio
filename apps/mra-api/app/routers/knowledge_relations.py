import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_knowledge_relation_service
from app.schemas import KnowledgeRelationCreate, KnowledgeRelationRead
from app.services.knowledge_relation_service import (
    KnowledgeRelationConflictError,
    KnowledgeRelationInvalidError,
    KnowledgeRelationNotFoundError,
    KnowledgeRelationService,
)

router = APIRouter(
    prefix="/api/v1/knowledge-cards/{source_id}/relations",
    tags=["knowledge-relations"],
)


@router.get("", response_model=list[KnowledgeRelationRead])
def list_relations(
    source_id: uuid.UUID,
    service: KnowledgeRelationService = Depends(get_knowledge_relation_service),
):
    try:
        return service.list_relations(source_id)
    except KnowledgeRelationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge Card non trovata.") from exc


@router.post(
    "",
    response_model=KnowledgeRelationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_relation(
    source_id: uuid.UUID,
    payload: KnowledgeRelationCreate,
    service: KnowledgeRelationService = Depends(get_knowledge_relation_service),
):
    try:
        return service.create_relation(source_id, payload)
    except KnowledgeRelationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Knowledge Card non trovata.") from exc
    except KnowledgeRelationInvalidError as exc:
        raise HTTPException(
            status_code=422,
            detail="Una Knowledge Card non può essere collegata a se stessa.",
        ) from exc
    except KnowledgeRelationConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Questa relazione esiste già.",
        ) from exc


@router.delete("/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relation(
    source_id: uuid.UUID,
    relation_id: uuid.UUID,
    service: KnowledgeRelationService = Depends(get_knowledge_relation_service),
) -> None:
    try:
        service.delete_relation(source_id, relation_id)
    except KnowledgeRelationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Relazione non trovata.") from exc
