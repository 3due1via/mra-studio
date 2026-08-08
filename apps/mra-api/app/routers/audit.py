import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_audit_service, require_admin
from app.schemas import AuditEventPage, AuditEventRead
from app.services.audit_service import AuditCursorError, AuditEventNotFoundError, AuditService

router = APIRouter(
    prefix="/api/v1/audit-events",
    tags=["audit"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=AuditEventPage)
def list_audit_events(
    actor_user_id: uuid.UUID | None = None,
    action: str | None = Query(default=None, max_length=100),
    entity_type: str | None = Query(default=None, max_length=60),
    entity_id: uuid.UUID | None = None,
    outcome: Literal["success", "failure"] | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    request_id: uuid.UUID | None = None,
    cursor: str | None = Query(default=None, max_length=512),
    limit: int = Query(default=50, ge=1, le=100),
    service: AuditService = Depends(get_audit_service),
) -> AuditEventPage:
    if occurred_from is not None and occurred_to is not None and occurred_from > occurred_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Intervallo temporale non valido.")
    try:
        events, next_cursor = service.list(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome=outcome,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            request_id=request_id,
            cursor=cursor,
            limit=limit,
        )
    except AuditCursorError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cursor non valido.") from exc
    return AuditEventPage(items=[AuditEventRead.model_validate(event) for event in events], next_cursor=next_cursor)


@router.get("/{event_id}", response_model=AuditEventRead)
def get_audit_event(
    event_id: uuid.UUID,
    service: AuditService = Depends(get_audit_service),
) -> AuditEventRead:
    try:
        return AuditEventRead.model_validate(service.get(event_id))
    except AuditEventNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento audit non trovato.") from exc
