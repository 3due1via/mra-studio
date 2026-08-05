from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories.knowledge_relation_repository import (
    SqlAlchemyKnowledgeRelationRepository,
)
from app.repositories.knowledge_repository import SqlAlchemyKnowledgeRepository
from app.repositories.knowledge_revision_repository import (
    SqlAlchemyKnowledgeRevisionRepository,
)
from app.services.knowledge_relation_service import KnowledgeRelationService
from app.services.knowledge_revision_service import KnowledgeRevisionService
from app.services.knowledge_service import KnowledgeService


def get_knowledge_revision_service_from_db(db: Session) -> KnowledgeRevisionService:
    return KnowledgeRevisionService(
        SqlAlchemyKnowledgeRevisionRepository(db),
        SqlAlchemyKnowledgeRepository(db),
    )


def get_knowledge_service(db: Session = Depends(get_db)) -> KnowledgeService:
    revision_service = get_knowledge_revision_service_from_db(db)
    return KnowledgeService(
        SqlAlchemyKnowledgeRepository(db),
        revision_service=revision_service,
    )


def get_knowledge_relation_service(
    db: Session = Depends(get_db),
) -> KnowledgeRelationService:
    knowledge_repository = SqlAlchemyKnowledgeRepository(db)
    return KnowledgeRelationService(
        SqlAlchemyKnowledgeRelationRepository(db),
        knowledge_repository,
    )


def get_knowledge_revision_service(
    db: Session = Depends(get_db),
) -> KnowledgeRevisionService:
    return get_knowledge_revision_service_from_db(db)
