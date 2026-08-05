import uuid
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import KnowledgeCard


class KnowledgeRepositoryProtocol(Protocol):
    def list(
        self,
        *,
        search: str | None = None,
        status_filter: str | None = None,
    ) -> Sequence[KnowledgeCard]: ...

    def get(self, card_id: uuid.UUID) -> KnowledgeCard | None: ...

    def get_by_code(self, code: str) -> KnowledgeCard | None: ...

    def add(self, card: KnowledgeCard) -> KnowledgeCard: ...

    def save(self, card: KnowledgeCard) -> KnowledgeCard: ...

    def delete(self, card: KnowledgeCard) -> None: ...


class SqlAlchemyKnowledgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        search: str | None = None,
        status_filter: str | None = None,
    ) -> Sequence[KnowledgeCard]:
        statement = select(KnowledgeCard).order_by(
            KnowledgeCard.updated_at.desc()
        )

        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    KnowledgeCard.code.ilike(term),
                    KnowledgeCard.title.ilike(term),
                    KnowledgeCard.category.ilike(term),
                )
            )

        if status_filter:
            statement = statement.where(
                KnowledgeCard.status == status_filter
            )

        return tuple(self.db.scalars(statement).all())

    def get(self, card_id: uuid.UUID) -> KnowledgeCard | None:
        return self.db.get(KnowledgeCard, card_id)

    def get_by_code(self, code: str) -> KnowledgeCard | None:
        statement = select(KnowledgeCard).where(
            KnowledgeCard.code == code
        )
        return self.db.scalar(statement)

    def add(self, card: KnowledgeCard) -> KnowledgeCard:
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        return card

    def save(self, card: KnowledgeCard) -> KnowledgeCard:
        self.db.commit()
        self.db.refresh(card)
        return card

    def delete(self, card: KnowledgeCard) -> None:
        self.db.delete(card)
        self.db.commit()
