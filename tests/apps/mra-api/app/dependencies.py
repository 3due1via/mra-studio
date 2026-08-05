from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories.knowledge_repository import (
    SqlAlchemyKnowledgeRepository,
)
from app.services.knowledge_service import KnowledgeService


def get_knowledge_service(
    db: Session = Depends(get_db),
) -> KnowledgeService:
    return KnowledgeService(
        SqlAlchemyKnowledgeRepository(db)
    )
