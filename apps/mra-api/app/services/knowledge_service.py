import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError

from app.models import KnowledgeCard
from app.repositories.knowledge_repository import (
    KnowledgeRepositoryProtocol,
)
from app.schemas import KnowledgeCardCreate, KnowledgeCardUpdate
from app.services.knowledge_revision_service import KnowledgeRevisionService
from app.services.audit_service import AuditService, KNOWLEDGE_CARD_CREATED, KNOWLEDGE_CARD_UPDATED, KNOWLEDGE_CARD_DELETED


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
        audit: AuditService | None = None,
    ) -> None:
        self.repository = repository
        self.revision_service = revision_service
        self.audit = audit

    @staticmethod
    def _snapshot(card: KnowledgeCard) -> dict:
        return {field: getattr(card, field) for field in KnowledgeRevisionService.SNAPSHOT_FIELDS}

    def _failure(self, card_id: uuid.UUID | None) -> None:
        if self.audit:
            self.audit.record_failure_after_rollback(entity_type="knowledge_card", entity_id=card_id, code="persistence_error", commit=self.repository.commit, rollback=self.repository.rollback)

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
            if self.audit:
                self.audit.record_change(action=KNOWLEDGE_CARD_CREATED, entity_type="knowledge_card", entity_id=created.id, before=None, after=self._snapshot(created))
            self.repository.commit()
            return created
        except IntegrityError as exc:
            self.repository.rollback()
            if _is_code_conflict(exc):
                raise KnowledgeCardCodeConflictError from exc
            self._failure(card.id)
            raise KnowledgePersistenceError from exc
        except Exception:
            self.repository.rollback()
            self._failure(card.id)
            raise

    def update_card(
        self,
        card_id: uuid.UUID,
        payload: KnowledgeCardUpdate,
    ) -> KnowledgeCard:
        card = self.get_card(card_id)
        before = self._snapshot(card)

        for field, value in payload.model_dump(
            exclude_unset=True
        ).items():
            setattr(card, field, value)

        try:
            saved = self.repository.save(card)
            if self.revision_service is not None:
                self.revision_service.record(saved, action="update")
            if self.audit:
                self.audit.record_change(action=KNOWLEDGE_CARD_UPDATED, entity_type="knowledge_card", entity_id=saved.id, before=before, after=self._snapshot(saved))
            self.repository.commit()
            return saved
        except IntegrityError as exc:
            self.repository.rollback()
            self._failure(card.id)
            raise KnowledgePersistenceError from exc
        except Exception:
            self.repository.rollback()
            self._failure(card.id)
            raise

    def delete_card(self, card_id: uuid.UUID) -> None:
        card = self.get_card(card_id)
        before = self._snapshot(card)
        try:
            self.repository.delete(card)
            if self.audit:
                self.audit.record_change(action=KNOWLEDGE_CARD_DELETED, entity_type="knowledge_card", entity_id=card.id, before=before, after=None)
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            self._failure(card.id)
            raise KnowledgePersistenceError from exc
        except Exception:
            self.repository.rollback()
            self._failure(card.id)
            raise
