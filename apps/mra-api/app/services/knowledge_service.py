import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError

from app.models import KnowledgeCard
from app.repositories.knowledge_repository import (
    KnowledgeRepositoryProtocol,
)
from app.schemas import KnowledgeCardCreate, KnowledgeCardUpdate
from app.services.knowledge_revision_service import KnowledgeRevisionService


class KnowledgeCardNotFoundError(Exception):
    pass


class KnowledgeCardCodeConflictError(Exception):
    pass


class KnowledgePersistenceError(Exception):
    pass


def _is_code_conflict(exc: IntegrityError) -> bool:
    diagnostic = getattr(exc.orig, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", "")
    return constraint in {"knowledge_cards_code_key", "ix_knowledge_cards_code"}


class KnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepositoryProtocol,
        revision_service: KnowledgeRevisionService | None = None,
    ) -> None:
        self.repository = repository
        self.revision_service = revision_service

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
            created = self.repository.add(card)
            if self.revision_service is not None:
                self.revision_service.record(created, action="create")
            self.repository.commit()
            return created
        except IntegrityError as exc:
            self.repository.rollback()
            if _is_code_conflict(exc):
                raise KnowledgeCardCodeConflictError from exc
            raise KnowledgePersistenceError from exc
        except Exception:
            self.repository.rollback()
            raise

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

        try:
            saved = self.repository.save(card)
            if self.revision_service is not None:
                self.revision_service.record(saved, action="update")
            self.repository.commit()
            return saved
        except IntegrityError as exc:
            self.repository.rollback()
            raise KnowledgePersistenceError from exc
        except Exception:
            self.repository.rollback()
            raise

    def delete_card(self, card_id: uuid.UUID) -> None:
        card = self.get_card(card_id)
        try:
            self.repository.delete(card)
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise KnowledgePersistenceError from exc
        except Exception:
            self.repository.rollback()
            raise
