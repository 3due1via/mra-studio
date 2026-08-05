import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeCard, KnowledgeRelation


class SqlAlchemyKnowledgeRelationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_source(
        self, source_id: uuid.UUID
    ) -> Sequence[tuple[KnowledgeRelation, KnowledgeCard]]:
        statement = (
            select(KnowledgeRelation, KnowledgeCard)
            .join(KnowledgeCard, KnowledgeCard.id == KnowledgeRelation.target_id)
            .where(KnowledgeRelation.source_id == source_id)
            .order_by(KnowledgeRelation.created_at.desc())
        )
        return tuple(self.db.execute(statement).all())

    def get(self, relation_id: uuid.UUID) -> KnowledgeRelation | None:
        return self.db.get(KnowledgeRelation, relation_id)

    def find_duplicate(
        self,
        *,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        relation_type: str,
    ) -> KnowledgeRelation | None:
        statement = select(KnowledgeRelation).where(
            KnowledgeRelation.source_id == source_id,
            KnowledgeRelation.target_id == target_id,
            KnowledgeRelation.relation_type == relation_type,
        )
        return self.db.scalar(statement)

    def add(self, relation: KnowledgeRelation) -> KnowledgeRelation:
        self.db.add(relation)
        self.db.commit()
        self.db.refresh(relation)
        return relation

    def delete(self, relation: KnowledgeRelation) -> None:
        self.db.delete(relation)
        self.db.commit()
