import uuid
from datetime import datetime

from sqlalchemy import Boolean, CHAR, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Sequence, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'editor', 'viewer')", name="ck_users_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="viewer", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("outcome IN ('success', 'failure')", name="ck_audit_events_outcome"),
        Index("ix_audit_events_occurred_id", "occurred_at", "id"),
        Index("ix_audit_events_actor_occurred", "actor_user_id", "occurred_at"),
        Index("ix_audit_events_action_occurred", "action", "occurred_at"),
        Index("ix_audit_events_entity_occurred", "entity_type", "entity_id", "occurred_at"),
        Index("ix_audit_events_outcome_occurred", "outcome", "occurred_at"),
        Index("ix_audit_events_request_id", "request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    actor_email_snapshot: Mapped[str | None] = mapped_column(String(320))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    outcome: Mapped[str] = mapped_column(String(20))
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    changed_fields: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    changes: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )


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


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    project_type: Mapped[str] = mapped_column(String(80), index=True)
    customer: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    environments: Mapped[list["Environment"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Environment(Base):
    __tablename__ = "environments"
    __table_args__ = (UniqueConstraint("id", "project_id", name="uq_environments_id_project"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    environment_type: Mapped[str] = mapped_column(String(80), index=True)
    area_m2: Mapped[str] = mapped_column(String(30), default="")
    height_m: Mapped[str] = mapped_column(String(30), default="")
    width_m: Mapped[str] = mapped_column(String(30), default="")
    length_m: Mapped[str] = mapped_column(String(30), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="environments")
    objects: Mapped[list["MraObject"]] = relationship(
        back_populates="environment", cascade="all, delete-orphan"
    )


class MraObject(Base):
    __tablename__ = "mra_objects"
    __table_args__ = (UniqueConstraint("id", "environment_id", name="uq_mra_objects_id_environment"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    brand: Mapped[str] = mapped_column(String(120), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    serial_number: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    environment: Mapped[Environment] = relationship(back_populates="objects")


intervention_code_sequence = Sequence("intervention_code_seq")


class Intervention(Base):
    __tablename__ = "interventions"
    __table_args__ = (
        CheckConstraint("status IN ('open','planned','in_progress','blocked','completed','cancelled')", name="ck_interventions_status"),
        CheckConstraint("priority IN ('low','normal','high','urgent')", name="ck_interventions_priority"),
        CheckConstraint("char_length(title) BETWEEN 1 AND 255", name="ck_interventions_title_length"),
        CheckConstraint("char_length(description) <= 10000", name="ck_interventions_description_length"),
        CheckConstraint("resolution_summary IS NULL OR char_length(resolution_summary) <= 5000", name="ck_interventions_resolution_length"),
        CheckConstraint("version >= 1", name="ck_interventions_version"),
        ForeignKeyConstraint(["environment_id", "project_id"], ["environments.id", "environments.project_id"], ondelete="RESTRICT", name="fk_interventions_environment_project"),
        ForeignKeyConstraint(["mra_object_id", "environment_id"], ["mra_objects.id", "mra_objects.environment_id"], ondelete="RESTRICT", name="fk_interventions_object_environment"),
        Index("ix_interventions_created_id", "created_at", "id"),
        Index("ix_interventions_scope", "project_id", "environment_id", "mra_object_id"),
        Index("ix_interventions_status_priority", "status", "priority"),
        Index("ix_interventions_assignee", "assigned_user_id"),
        Index("ix_interventions_due_at", "due_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, server_default=text("'INT-' || lpad(nextval('intervention_code_seq')::text, 6, '0')"))
    client_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    client_request_fingerprint: Mapped[str] = mapped_column(CHAR(64))
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT", name="fk_interventions_project"))
    environment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("environments.id", ondelete="RESTRICT", name="fk_interventions_environment"))
    mra_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mra_objects.id", ondelete="RESTRICT", name="fk_interventions_object"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    status: Mapped[str] = mapped_column(String(20), default="open", server_default=text("'open'"))
    priority: Mapped[str] = mapped_column(String(20), default="normal", server_default=text("'normal'"))
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT", name="fk_interventions_assigned_user"))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT", name="fk_interventions_created_by"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_summary: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __mapper_args__ = {"version_id_col": version, "version_id_generator": lambda value: (value or 0) + 1}


class InterventionEvent(Base):
    __tablename__ = "intervention_events"
    __table_args__ = (
        CheckConstraint("event_type IN ('intervention_created','assignment_changed','status_changed','reopened','knowledge_linked','knowledge_unlinked')", name="ck_intervention_events_type"),
        CheckConstraint("note IS NULL OR char_length(note) <= 1000", name="ck_intervention_events_note_length"),
        CheckConstraint("resolution_summary_snapshot IS NULL OR char_length(resolution_summary_snapshot) <= 5000", name="ck_intervention_events_resolution_length"),
        Index("ix_intervention_events_timeline", "intervention_id", "occurred_at", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intervention_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interventions.id", ondelete="RESTRICT"))
    event_type: Mapped[str] = mapped_column(String(40))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    actor_display_name_snapshot: Mapped[str] = mapped_column(String(120))
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    note: Mapped[str | None] = mapped_column(Text)
    resolution_summary_snapshot: Mapped[str | None] = mapped_column(Text)
    command_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    command_fingerprint: Mapped[str | None] = mapped_column(CHAR(64))
    result_version: Mapped[int | None] = mapped_column(Integer)
    result_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InterventionKnowledgeLink(Base):
    __tablename__ = "intervention_knowledge_links"
    __table_args__ = (
        UniqueConstraint("intervention_id", "knowledge_card_id", "usage_type", name="uq_intervention_knowledge_link"),
        CheckConstraint("usage_type IN ('diagnostic_reference','procedure_applied','solution_used')", name="ck_intervention_knowledge_links_usage"),
        CheckConstraint("char_length(note) <= 500", name="ck_intervention_knowledge_links_note_length"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intervention_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interventions.id", ondelete="RESTRICT"), index=True)
    knowledge_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_cards.id", ondelete="RESTRICT", name="fk_intervention_knowledge_links_card"), index=True)
    usage_type: Mapped[str] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(String(500), default="", server_default=text("''"))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
