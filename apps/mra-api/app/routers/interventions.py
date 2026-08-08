import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_intervention_service, require_csrf, require_editor, require_viewer
from app.models import User
from app.schemas import InterventionAssigneeRead, InterventionCreate, InterventionEventRead, InterventionKnowledgeCreate, InterventionKnowledgeRead, InterventionPage, InterventionRead, InterventionSummary, InterventionTransition, InterventionTransitionResult, InterventionUpdate
from app.services.intervention_service import InterventionConflictError, InterventionNotFoundError, InterventionPermissionError, InterventionPersistenceError, InterventionService, InterventionValidationError, KnowledgeCardNotFoundError

router = APIRouter(prefix="/api/v1/interventions", tags=["interventions"], dependencies=[Depends(require_viewer)])


def errors(exc: Exception):
    if isinstance(exc, InterventionNotFoundError): return HTTPException(404, "Intervento non trovato.")
    if isinstance(exc, KnowledgeCardNotFoundError): return HTTPException(404, "Collegamento o scheda Knowledge non trovato.")
    if isinstance(exc, InterventionConflictError): return HTTPException(409, "Conflitto con lo stato corrente dell'intervento.")
    if isinstance(exc, InterventionPermissionError): return HTTPException(403, "Permessi insufficienti.")
    if isinstance(exc, InterventionValidationError): return HTTPException(422, str(exc) or "Dati intervento non validi.")
    return HTTPException(500, "Impossibile salvare l'intervento.")


@router.get("", response_model=InterventionPage)
def list_interventions(project_id: uuid.UUID | None = None, environment_id: uuid.UUID | None = None, mra_object_id: uuid.UUID | None = None, assigned_user_id: uuid.UUID | None = None, status_filter: Literal["open","planned","in_progress","blocked","completed","cancelled"] | None = Query(None, alias="status"), priority: Literal["low","normal","high","urgent"] | None = None, created_by_user_id: uuid.UUID | None = None, due_from: datetime | None = None, due_to: datetime | None = None, overdue: bool | None = None, search: str | None = Query(None, max_length=255), cursor: str | None = Query(None, max_length=512), limit: int = Query(50, ge=1, le=100), service: InterventionService = Depends(get_intervention_service)):
    if due_from and due_to and due_from > due_to: raise HTTPException(422, "Intervallo scadenza non valido.")
    try:
        items, next_cursor = service.list(project_id=project_id, environment_id=environment_id, mra_object_id=mra_object_id, assigned_user_id=assigned_user_id, status=status_filter, priority=priority, created_by_user_id=created_by_user_id, due_from=due_from, due_to=due_to, overdue=overdue, search=search, cursor=cursor, limit=limit)
        return InterventionPage(items=[InterventionRead.model_validate(item) for item in items], next_cursor=next_cursor)
    except InterventionValidationError as exc: raise errors(exc) from exc


@router.get("/summary", response_model=InterventionSummary)
def summary(service: InterventionService = Depends(get_intervention_service)): return service.summary()


@router.get("/assignees", response_model=list[InterventionAssigneeRead], dependencies=[Depends(require_editor)])
def assignees(service: InterventionService = Depends(get_intervention_service)): return service.assignees()


@router.post("", response_model=InterventionRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create(payload: InterventionCreate, actor: User = Depends(require_editor), service: InterventionService = Depends(get_intervention_service)):
    try: return service.create(payload, actor)
    except (InterventionConflictError, InterventionValidationError, InterventionPersistenceError) as exc: raise errors(exc) from exc


@router.get("/{intervention_id}", response_model=InterventionRead)
def get(intervention_id: uuid.UUID, service: InterventionService = Depends(get_intervention_service)):
    try: return service.get(intervention_id)
    except InterventionNotFoundError as exc: raise errors(exc) from exc


@router.patch("/{intervention_id}", response_model=InterventionRead, dependencies=[Depends(require_csrf)])
def update(intervention_id: uuid.UUID, payload: InterventionUpdate, actor: User = Depends(require_editor), service: InterventionService = Depends(get_intervention_service)):
    try: return service.update(intervention_id, payload, actor)
    except (InterventionNotFoundError, InterventionConflictError, InterventionValidationError, InterventionPersistenceError) as exc: raise errors(exc) from exc


@router.post("/{intervention_id}/transitions", response_model=InterventionTransitionResult, dependencies=[Depends(require_csrf)])
def transition(intervention_id: uuid.UUID, payload: InterventionTransition, actor: User = Depends(require_editor), service: InterventionService = Depends(get_intervention_service)):
    try: return service.transition(intervention_id, payload, actor)
    except (InterventionNotFoundError, InterventionConflictError, InterventionPermissionError, InterventionPersistenceError) as exc: raise errors(exc) from exc


@router.get("/{intervention_id}/timeline", response_model=list[InterventionEventRead])
def timeline(intervention_id: uuid.UUID, service: InterventionService = Depends(get_intervention_service)):
    try: return service.timeline(intervention_id)
    except InterventionNotFoundError as exc: raise errors(exc) from exc


@router.get("/{intervention_id}/knowledge", response_model=list[InterventionKnowledgeRead])
def knowledge(intervention_id: uuid.UUID, service: InterventionService = Depends(get_intervention_service)):
    try: return service.knowledge(intervention_id)
    except InterventionNotFoundError as exc: raise errors(exc) from exc


@router.post("/{intervention_id}/knowledge", response_model=InterventionKnowledgeRead, status_code=201, dependencies=[Depends(require_csrf)])
def link_knowledge(intervention_id: uuid.UUID, payload: InterventionKnowledgeCreate, actor: User = Depends(require_editor), service: InterventionService = Depends(get_intervention_service)):
    try: return service.link_knowledge(intervention_id, payload, actor)
    except (InterventionNotFoundError, KnowledgeCardNotFoundError, InterventionConflictError, InterventionPersistenceError) as exc: raise errors(exc) from exc


@router.delete("/{intervention_id}/knowledge/{link_id}", status_code=204, dependencies=[Depends(require_csrf)])
def unlink_knowledge(intervention_id: uuid.UUID, link_id: uuid.UUID, actor: User = Depends(require_editor), service: InterventionService = Depends(get_intervention_service)):
    try: service.unlink_knowledge(intervention_id, link_id, actor)
    except (InterventionNotFoundError, KnowledgeCardNotFoundError, InterventionConflictError, InterventionPersistenceError) as exc: raise errors(exc) from exc
