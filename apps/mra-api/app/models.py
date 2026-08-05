import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class KnowledgeCard(Base):
    __tablename__ = "knowledge_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    summary: Mapped[str] = mapped_column(Text, default="")
    symptoms: Mapped[str] = mapped_column(Text, default="")
    causes: Mapped[str] = mapped_column(Text, default="")
    diagnosis: Mapped[str] = mapped_column(Text, default="")
    procedure: Mapped[str] = mapped_column(Text, default="")
    tools: Mapped[str] = mapped_column(Text, default="")
    safety: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KnowledgeRelation(Base):
    __tablename__ = "knowledge_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "target_id",
            "relation_type",
            name="uq_knowledge_relation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_cards.id", ondelete="CASCADE"),
        index=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_cards.id", ondelete="CASCADE"),
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(40), index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped[KnowledgeCard] = relationship(
        foreign_keys=[source_id]
    )
    target: Mapped[KnowledgeCard] = relationship(
        foreign_keys=[target_id]
    )


class KnowledgeRevision(Base):
    __tablename__ = "knowledge_revisions"
    __table_args__ = (
        UniqueConstraint(
            "card_id",
            "revision_number",
            name="uq_knowledge_revision_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_cards.id", ondelete="CASCADE"),
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(30), default="update")
    note: Mapped[str] = mapped_column(Text, default="")
    snapshot: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped[KnowledgeCard] = relationship(foreign_keys=[card_id])
