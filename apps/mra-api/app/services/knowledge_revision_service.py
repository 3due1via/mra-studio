import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.models import KnowledgeCard, KnowledgeRevision
from app.repositories.knowledge_repository import KnowledgeRepositoryProtocol
from app.repositories.knowledge_revision_repository import (
    KnowledgeRevisionRepositoryProtocol,
)
from app.services.audit_service import AuditService, KNOWLEDGE_REVISION_RESTORED


class KnowledgeRevisionNotFoundError(Exception):
    pass


class KnowledgeRevisionPersistenceError(Exception):
    pass


class KnowledgeRevisionService:
    SNAPSHOT_FIELDS = (
        "code",
        "title",
        "category",
        "status",
        "version",
        "summary",
        "symptoms",
        "causes",
        "diagnosis",
        "procedure",
        "tools",
        "safety",
    )

    def __init__(
        self,
        revision_repository: KnowledgeRevisionRepositoryProtocol,
        knowledge_repository: KnowledgeRepositoryProtocol,
        audit: AuditService | None = None,
    ) -> None:
        self.revision_repository = revision_repository
        self.knowledge_repository = knowledge_repository
        self.audit = audit

    def list_revisions(self, card_id: uuid.UUID) -> Sequence[KnowledgeRevision]:
        self._get_card(card_id)
        return self.revision_repository.list_for_card(card_id)

    def record(
        self,
        card: KnowledgeCard,
        *,
        action: str,
        note: str = "",
    ) -> KnowledgeRevision:
        return self.revision_repository.add(
            card_id=card.id,
            action=action,
            note=note,
            snapshot=self.snapshot(card),
        )

    def restore(
        self,
        card_id: uuid.UUID,
        revision_id: uuid.UUID,
    ) -> KnowledgeCard:
        card = self._get_card(card_id)
        before = self.snapshot(card)
        revision = self.revision_repository.get(card_id, revision_id)
        if revision is None:
            raise KnowledgeRevisionNotFoundError

        for field in self.SNAPSHOT_FIELDS:
            if field in revision.snapshot:
                setattr(card, field, revision.snapshot[field])

        try:
            restored = self.knowledge_repository.save(card)
            self.record(
                restored,
                action="restore",
                note=f"Ripristinata revisione #{revision.revision_number}",
            )
            if self.audit:
                self.audit.record_change(action=KNOWLEDGE_REVISION_RESTORED, entity_type="knowledge_card", entity_id=card.id, before=before, after=self.snapshot(restored))
            self.knowledge_repository.commit()
            return restored
        except IntegrityError as exc:
            self.knowledge_repository.rollback()
            if self.audit:
                self.audit.record_failure_after_rollback(entity_type="knowledge_card", entity_id=card.id, code="persistence_error", commit=self.knowledge_repository.commit, rollback=self.knowledge_repository.rollback)
            raise KnowledgeRevisionPersistenceError from exc
        except Exception:
            self.knowledge_repository.rollback()
            if self.audit:
                self.audit.record_failure_after_rollback(entity_type="knowledge_card", entity_id=card.id, code="persistence_error", commit=self.knowledge_repository.commit, rollback=self.knowledge_repository.rollback)
            raise

    @classmethod
    def snapshot(cls, card: KnowledgeCard) -> dict[str, Any]:
        return {field: getattr(card, field) for field in cls.SNAPSHOT_FIELDS}

    def _get_card(self, card_id: uuid.UUID) -> KnowledgeCard:
        card = self.knowledge_repository.get(card_id)
        if card is None:
            raise KnowledgeRevisionNotFoundError
        return card
