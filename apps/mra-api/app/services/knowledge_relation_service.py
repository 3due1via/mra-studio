import uuid

from app.models import KnowledgeRelation
from app.repositories.knowledge_relation_repository import (
    SqlAlchemyKnowledgeRelationRepository,
)
from app.repositories.knowledge_repository import KnowledgeRepositoryProtocol
from app.schemas import KnowledgeRelationCreate, KnowledgeRelationRead


class KnowledgeRelationNotFoundError(Exception):
    pass


class KnowledgeRelationConflictError(Exception):
    pass


class KnowledgeRelationInvalidError(Exception):
    pass


class KnowledgeRelationService:
    def __init__(
        self,
        relation_repository: SqlAlchemyKnowledgeRelationRepository,
        knowledge_repository: KnowledgeRepositoryProtocol,
    ) -> None:
        self.relation_repository = relation_repository
        self.knowledge_repository = knowledge_repository

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

        relation = self.relation_repository.add(
            KnowledgeRelation(
                source_id=source_id,
                target_id=payload.target_id,
                relation_type=payload.relation_type,
                note=payload.note.strip(),
            )
        )
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
        self.relation_repository.delete(relation)
