import uuid
from collections.abc import Sequence
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import KnowledgeRevision


class KnowledgeRevisionRepositoryProtocol(Protocol):
    def list_for_card(self, card_id: uuid.UUID) -> Sequence[KnowledgeRevision]: ...

    def get(
        self,
        card_id: uuid.UUID,
        revision_id: uuid.UUID,
    ) -> KnowledgeRevision | None: ...

    def add(
        self,
        *,
        card_id: uuid.UUID,
        action: str,
        snapshot: dict[str, Any],
        note: str = "",
    ) -> KnowledgeRevision: ...


class SqlAlchemyKnowledgeRevisionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_card(self, card_id: uuid.UUID) -> Sequence[KnowledgeRevision]:
        statement = (
            select(KnowledgeRevision)
            .where(KnowledgeRevision.card_id == card_id)
            .order_by(KnowledgeRevision.revision_number.desc())
        )
        return tuple(self.db.scalars(statement).all())

    def get(
        self,
        card_id: uuid.UUID,
        revision_id: uuid.UUID,
    ) -> KnowledgeRevision | None:
        statement = select(KnowledgeRevision).where(
            KnowledgeRevision.id == revision_id,
            KnowledgeRevision.card_id == card_id,
        )
        return self.db.scalar(statement)

    def add(
        self,
        *,
        card_id: uuid.UUID,
        action: str,
        snapshot: dict[str, Any],
        note: str = "",
    ) -> KnowledgeRevision:
        current_number = self.db.scalar(
            select(func.max(KnowledgeRevision.revision_number)).where(
                KnowledgeRevision.card_id == card_id
            )
        )
        revision = KnowledgeRevision(
            card_id=card_id,
            revision_number=(current_number or 0) + 1,
            action=action,
            note=note,
            snapshot=snapshot,
        )
        self.db.add(revision)
        self.db.commit()
        self.db.refresh(revision)
        return revision
