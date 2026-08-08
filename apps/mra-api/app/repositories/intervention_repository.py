import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import Environment, Intervention, InterventionEvent, InterventionKnowledgeLink, KnowledgeCard, MraObject, User


class SqlAlchemyInterventionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_intervention(self, value: Intervention) -> Intervention:
        self.db.add(value); self.db.flush(); return value

    def add_event(self, value: InterventionEvent) -> InterventionEvent:
        self.db.add(value); self.db.flush(); return value

    def add_knowledge_link(self, value: InterventionKnowledgeLink) -> InterventionKnowledgeLink:
        self.db.add(value); self.db.flush(); return value

    def get(self, intervention_id: uuid.UUID, *, lock: bool = False) -> Intervention | None:
        statement = select(Intervention).where(Intervention.id == intervention_id)
        if lock: statement = statement.with_for_update()
        return self.db.scalar(statement)

    def get_by_request_id(self, request_id: uuid.UUID) -> Intervention | None:
        return self.db.scalar(select(Intervention).where(Intervention.client_request_id == request_id))

    def get_command(self, command_id: uuid.UUID) -> InterventionEvent | None:
        return self.db.scalar(select(InterventionEvent).where(InterventionEvent.command_id == command_id))

    def get_user(self, user_id: uuid.UUID | None) -> User | None:
        return self.db.get(User, user_id) if user_id else None

    def list_assignees(self) -> Sequence[User]:
        return tuple(self.db.scalars(select(User).where(User.is_active.is_(True), User.role.in_(("editor", "admin"))).order_by(User.display_name.asc(), User.id.asc())).all())

    def hierarchy_valid(self, project_id, environment_id, object_id) -> bool:
        return self.db.scalar(select(func.count()).select_from(MraObject).join(Environment, MraObject.environment_id == Environment.id).where(Environment.project_id == project_id, Environment.id == environment_id, MraObject.id == object_id)) == 1

    def knowledge_exists(self, card_id: uuid.UUID) -> bool:
        return self.db.get(KnowledgeCard, card_id) is not None

    def list(self, *, cursor=None, limit=50, search=None, overdue=None, now=None, **filters) -> Sequence[Intervention]:
        statement = select(Intervention)
        for field in ("project_id", "environment_id", "mra_object_id", "assigned_user_id", "status", "priority", "created_by_user_id"):
            value = filters.get(field)
            if value is not None: statement = statement.where(getattr(Intervention, field) == value)
        if filters.get("due_from") is not None: statement = statement.where(Intervention.due_at >= filters["due_from"])
        if filters.get("due_to") is not None: statement = statement.where(Intervention.due_at <= filters["due_to"])
        if overdue is not None:
            boundary = now or datetime.now(timezone.utc)
            condition = and_(Intervention.due_at.is_not(None), Intervention.due_at < boundary, Intervention.status.not_in(("completed", "cancelled")))
            complement = or_(Intervention.due_at.is_(None), Intervention.due_at >= boundary, Intervention.status.in_(("completed", "cancelled")))
            statement = statement.where(condition if overdue else complement)
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"; statement = statement.where(or_(Intervention.code.ilike(pattern, escape="\\"), Intervention.title.ilike(pattern, escape="\\")))
        if cursor:
            created_at, item_id = cursor; statement = statement.where(or_(Intervention.created_at < created_at, and_(Intervention.created_at == created_at, Intervention.id < item_id)))
        return tuple(self.db.scalars(statement.order_by(Intervention.created_at.desc(), Intervention.id.desc()).limit(limit)).all())

    def summary(self, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.now(timezone.utc); recent = now - timedelta(days=30)
        def count(*conditions): return int(self.db.scalar(select(func.count()).select_from(Intervention).where(*conditions)) or 0)
        return {"open": count(Intervention.status == "open"), "in_progress": count(Intervention.status == "in_progress"), "overdue": count(Intervention.due_at < now, Intervention.status.not_in(("completed", "cancelled"))), "recently_completed": count(Intervention.status == "completed", Intervention.completed_at >= recent)}

    def timeline(self, intervention_id: uuid.UUID):
        return tuple(self.db.scalars(select(InterventionEvent).where(InterventionEvent.intervention_id == intervention_id).order_by(InterventionEvent.occurred_at.asc(), InterventionEvent.id.asc())).all())

    def knowledge(self, intervention_id: uuid.UUID):
        return tuple(self.db.scalars(select(InterventionKnowledgeLink).where(InterventionKnowledgeLink.intervention_id == intervention_id).order_by(InterventionKnowledgeLink.created_at.asc())).all())

    def get_link(self, link_id: uuid.UUID): return self.db.get(InterventionKnowledgeLink, link_id)
    def delete_knowledge_link(self, value: InterventionKnowledgeLink): self.db.delete(value); self.db.flush()
    def flush(self): self.db.flush()
    def refresh(self, value): self.db.refresh(value)
    def commit(self): self.db.commit()
    def rollback(self): self.db.rollback()
