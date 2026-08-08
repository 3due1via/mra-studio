import uuid

from sqlalchemy.exc import IntegrityError

from app.models import KnowledgeRelation
from app.repositories.knowledge_relation_repository import (
    SqlAlchemyKnowledgeRelationRepository,
)
from app.repositories.knowledge_repository import KnowledgeRepositoryProtocol
from app.schemas import KnowledgeRelationCreate, KnowledgeRelationRead
from app.services.audit_service import AuditService, KNOWLEDGE_RELATION_CREATED, KNOWLEDGE_RELATION_DELETED


class KnowledgeRelationNotFoundError(Exception):
    pass


class KnowledgeRelationConflictError(Exception):
    pass


class KnowledgeRelationInvalidError(Exception):
    pass


class KnowledgeRelationPersistenceError(Exception):
    pass


def _is_relation_conflict(exc: IntegrityError) -> bool:
    return str(getattr(getattr(exc.orig, "diag", None), "constraint_name", "") or "") == "uq_knowledge_relation"


class KnowledgeRelationService:
    def __init__(
        self,
        relation_repository: SqlAlchemyKnowledgeRelationRepository,
        knowledge_repository: KnowledgeRepositoryProtocol,
        audit: AuditService | None = None,
    ) -> None:
        self.relation_repository = relation_repository
        self.knowledge_repository = knowledge_repository
        self.audit = audit

    def list_relations(self, source_id: uuid.UUID) -> list[KnowledgeRelationRead]:
        if self.knowledge_repository.get(source_id) is None:
            raise KnowledgeRelationNotFoundError

        return [
            KnowledgeRelationRead(
                id=relation.id,
                source_id=relation.source_id,
                target_id=relation.target_id,
                relation_type=relation.relation_type,
                note=relation.note,
                target_code=target.code,
                target_title=target.title,
                target_category=target.category,
                created_at=relation.created_at,
            )
            for relation, target in self.relation_repository.list_for_source(source_id)
        ]

    def create_relation(
        self,
        source_id: uuid.UUID,
        payload: KnowledgeRelationCreate,
    ) -> KnowledgeRelationRead:
        source = self.knowledge_repository.get(source_id)
        target = self.knowledge_repository.get(payload.target_id)
        if source is None or target is None:
            raise KnowledgeRelationNotFoundError
        if source_id == payload.target_id:
            raise KnowledgeRelationInvalidError
        if self.relation_repository.find_duplicate(
            source_id=source_id,
            target_id=payload.target_id,
            relation_type=payload.relation_type,
        ):
            raise KnowledgeRelationConflictError

        try:
            relation = self.relation_repository.add(
                KnowledgeRelation(
                    source_id=source_id,
                    target_id=payload.target_id,
                    relation_type=payload.relation_type,
                    note=payload.note.strip(),
                )
            )
        except IntegrityError as exc:
            self.relation_repository.rollback()
            if _is_relation_conflict(exc):
                raise KnowledgeRelationConflictError from exc
            if self.audit:
                self.audit.record_failure_after_rollback(entity_type="knowledge_relation", entity_id=None, code="persistence_error", commit=self.relation_repository.commit, rollback=self.relation_repository.rollback)
            raise KnowledgeRelationPersistenceError from exc
        except Exception:
            self.relation_repository.rollback()
            if self.audit:
                self.audit.record_failure_after_rollback(entity_type="knowledge_relation", entity_id=None, code="persistence_error", commit=self.relation_repository.commit, rollback=self.relation_repository.rollback)
            raise
        try:
            if self.audit:
                self.audit.record(action=KNOWLEDGE_RELATION_CREATED, entity_type="knowledge_relation", entity_id=relation.id, changed_fields=["source_id", "target_id", "relation_type"], changes={"source_id": {"after": str(source_id)}, "target_id": {"after": str(payload.target_id)}, "relation_type": {"after": payload.relation_type}})
            self.relation_repository.commit()
        except Exception as exc:
            self.relation_repository.rollback()
            if self.audit:
                self.audit.record_failure_after_rollback(entity_type="knowledge_relation", entity_id=relation.id, code="persistence_error", commit=self.relation_repository.commit, rollback=self.relation_repository.rollback)
            raise KnowledgeRelationPersistenceError from exc
        return KnowledgeRelationRead(
            id=relation.id,
            source_id=relation.source_id,
            target_id=relation.target_id,
            relation_type=relation.relation_type,
            note=relation.note,
            target_code=target.code,
            target_title=target.title,
            target_category=target.category,
            created_at=relation.created_at,
        )

    def delete_relation(
        self, source_id: uuid.UUID, relation_id: uuid.UUID
    ) -> None:
        relation = self.relation_repository.get(relation_id)
        if relation is None or relation.source_id != source_id:
            raise KnowledgeRelationNotFoundError
        try:
            self.relation_repository.delete(relation)
            if self.audit:
                self.audit.record(
                    action=KNOWLEDGE_RELATION_DELETED,
                    entity_type="knowledge_relation",
                    entity_id=relation.id,
                    changed_fields=["source_id", "target_id", "relation_type"],
                    changes={
                        "source_id": {"before": str(relation.source_id)},
                        "target_id": {"before": str(relation.target_id)},
                        "relation_type": {"before": relation.relation_type},
                    },
                )
            self.relation_repository.commit()
        except IntegrityError as exc:
            self.relation_repository.rollback()
            if self.audit:
                self.audit.record_failure_after_rollback(entity_type="knowledge_relation", entity_id=relation.id, code="persistence_error", commit=self.relation_repository.commit, rollback=self.relation_repository.rollback)
            raise KnowledgeRelationPersistenceError from exc
        except Exception:
            self.relation_repository.rollback()
            if self.audit:
                self.audit.record_failure_after_rollback(entity_type="knowledge_relation", entity_id=relation.id, code="persistence_error", commit=self.relation_repository.commit, rollback=self.relation_repository.rollback)
            raise
