import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError

from app.models import KnowledgeCard
from app.repositories.knowledge_repository import (
    KnowledgeRepositoryProtocol,
)
from app.schemas import KnowledgeCardCreate, KnowledgeCardUpdate


class KnowledgeCardNotFoundError(Exception):
    pass


class KnowledgeCardCodeConflictError(Exception):
    pass


class KnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepositoryProtocol,
    ) -> None:
        self.repository = repository

    def list_cards(
        self,
        *,
        search: str | None = None,
        status_filter: str | None = None,
    ) -> Sequence[KnowledgeCard]:
        return self.repository.list(
            search=search,
            status_filter=status_filter,
        )

    def get_card(self, card_id: uuid.UUID) -> KnowledgeCard:
        card = self.repository.get(card_id)
        if card is None:
            raise KnowledgeCardNotFoundError
        return card

    def create_card(
        self,
        payload: KnowledgeCardCreate,
    ) -> KnowledgeCard:
        if self.repository.get_by_code(payload.code) is not None:
            raise KnowledgeCardCodeConflictError

        card = KnowledgeCard(**payload.model_dump())

        try:
            return self.repository.add(card)
        except IntegrityError as exc:
            raise KnowledgeCardCodeConflictError from exc

    def update_card(
        self,
        card_id: uuid.UUID,
        payload: KnowledgeCardUpdate,
    ) -> KnowledgeCard:
        card = self.get_card(card_id)

        for field, value in payload.model_dump(
            exclude_unset=True
        ).items():
            setattr(card, field, value)

        return self.repository.save(card)

    def delete_card(self, card_id: uuid.UUID) -> None:
        card = self.get_card(card_id)
        self.repository.delete(card)
