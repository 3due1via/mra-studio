import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import AuditEvent


class AuditRepositoryProtocol(Protocol):
    def add(self, event: AuditEvent) -> AuditEvent: ...
    def get(self, event_id: uuid.UUID) -> AuditEvent | None: ...
    def list(
        self,
        *,
        actor_user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        outcome: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        request_id: uuid.UUID | None = None,
        cursor: tuple[datetime, uuid.UUID] | None = None,
        limit: int = 50,
    ) -> Sequence[AuditEvent]: ...


class SqlAlchemyAuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, event: AuditEvent) -> AuditEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def get(self, event_id: uuid.UUID) -> AuditEvent | None:
        return self.db.get(AuditEvent, event_id)

    def list(
        self,
        *,
        actor_user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        outcome: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        request_id: uuid.UUID | None = None,
        cursor: tuple[datetime, uuid.UUID] | None = None,
        limit: int = 50,
    ) -> Sequence[AuditEvent]:
        statement = select(AuditEvent)
        filters = {
            AuditEvent.actor_user_id: actor_user_id,
            AuditEvent.action: action,
            AuditEvent.entity_type: entity_type,
            AuditEvent.entity_id: entity_id,
            AuditEvent.outcome: outcome,
            AuditEvent.request_id: request_id,
        }
        for column, value in filters.items():
            if value is not None:
                statement = statement.where(column == value)
        if occurred_from is not None:
            statement = statement.where(AuditEvent.occurred_at >= occurred_from)
        if occurred_to is not None:
            statement = statement.where(AuditEvent.occurred_at <= occurred_to)
        if cursor is not None:
            occurred_at, event_id = cursor
            statement = statement.where(
                or_(
                    AuditEvent.occurred_at < occurred_at,
                    and_(AuditEvent.occurred_at == occurred_at, AuditEvent.id < event_id),
                )
            )
        statement = statement.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc()).limit(limit)
        return tuple(self.db.scalars(statement).all())
