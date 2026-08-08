import base64, hashlib, json, uuid
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.models import Intervention, InterventionEvent, InterventionKnowledgeLink, User
from app.repositories.intervention_repository import SqlAlchemyInterventionRepository
from app.schemas import InterventionCreate, InterventionKnowledgeCreate, InterventionTransition, InterventionTransitionResult, InterventionUpdate
from app.services.audit_service import AuditService, INTERVENTION_ASSIGNED, INTERVENTION_CANCELLED, INTERVENTION_CREATED, INTERVENTION_KNOWLEDGE_LINKED, INTERVENTION_KNOWLEDGE_UNLINKED, INTERVENTION_REOPENED, INTERVENTION_STATUS_CHANGED, INTERVENTION_UPDATED
from app.services.intervention_state_machine import InvalidTransitionError, apply_transition


class InterventionNotFoundError(Exception): pass
class InterventionConflictError(Exception): pass
class InterventionValidationError(Exception): pass
class InterventionPersistenceError(Exception): pass
class KnowledgeCardNotFoundError(Exception): pass
class InterventionPermissionError(Exception): pass


def canonical_fingerprint(payload: dict[str, Any], actor_id: uuid.UUID) -> str:
    def convert(value):
        if isinstance(value, (uuid.UUID, datetime)): return str(value) if isinstance(value, uuid.UUID) else value.isoformat()
        return value
    canonical = {key: convert(value) for key, value in payload.items()}
    canonical["actor_user_id"] = str(actor_id)
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _signature(filters: dict) -> str:
    clean = {key: (value.isoformat() if isinstance(value, datetime) else str(value)) for key, value in sorted(filters.items()) if value is not None}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]


def _encode_cursor(item: Intervention, signature: str) -> str:
    return base64.urlsafe_b64encode(json.dumps([item.created_at.isoformat(), str(item.id), signature], separators=(",", ":")).encode()).decode().rstrip("=")


def _decode_cursor(value: str):
    try:
        parsed = json.loads(base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)); timestamp = datetime.fromisoformat(parsed[0]); item_id = uuid.UUID(parsed[1])
        if len(parsed) != 3 or timestamp.tzinfo is None: raise ValueError
        return timestamp, item_id, parsed[2]
    except Exception as exc: raise InterventionValidationError("Cursor non valido.") from exc


class InterventionService:
    def __init__(self, repository: SqlAlchemyInterventionRepository, audit: AuditService): self.repository, self.audit = repository, audit

    @staticmethod
    def _snapshot(item: Intervention):
        return {field: (str(value) if isinstance(value, uuid.UUID) else value.isoformat() if isinstance(value, datetime) else value) for field in ("title", "description", "status", "priority", "assigned_user_id", "due_at", "started_at", "completed_at", "cancelled_at", "resolution_summary", "version") if (value := getattr(item, field)) is not None}

    def _assignee(self, user_id):
        if user_id is None: return None
        user = self.repository.get_user(user_id)
        if user is None or not user.is_active or user.role not in {"editor", "admin"}: raise InterventionValidationError("Assegnatario non valido.")
        return user

    def _event(self, item, actor, event_type, **values):
        return self.repository.add_event(InterventionEvent(intervention_id=item.id, event_type=event_type, actor_user_id=actor.id, actor_display_name_snapshot=actor.display_name, **values))

    @staticmethod
    def _transition_result(event: InterventionEvent) -> InterventionTransitionResult:
        return InterventionTransitionResult(
            intervention_id=event.intervention_id,
            command_id=event.command_id,
            from_status=event.from_status,
            to_status=event.to_status,
            result_version=event.result_version,
            started_at=event.result_started_at,
            completed_at=event.result_completed_at,
            cancelled_at=event.result_cancelled_at,
            occurred_at=event.occurred_at,
        )

    def _failure(self, entity_id): self.audit.record_failure_after_rollback(entity_type="intervention", entity_id=entity_id, code="intervention_persistence_error", commit=self.repository.commit, rollback=self.repository.rollback)

    def _unexpected(self, exc, entity_id):
        self.repository.rollback(); self._failure(entity_id); raise InterventionPersistenceError from exc

    def get(self, item_id):
        item = self.repository.get(item_id)
        if item is None: raise InterventionNotFoundError
        return item

    def list(self, *, cursor=None, limit=50, **filters):
        signature = _signature(filters); position = None
        if cursor:
            decoded = _decode_cursor(cursor)
            if decoded[2] != signature: raise InterventionValidationError("Cursor non valido.")
            position = decoded[:2]
        rows = tuple(self.repository.list(cursor=position, limit=limit + 1, **filters)); page = rows[:limit]
        return page, (_encode_cursor(page[-1], signature) if len(rows) > limit and page else None)

    def summary(self): return self.repository.summary()
    def assignees(self): return self.repository.list_assignees()

    def create(self, payload: InterventionCreate, actor: User):
        values = payload.model_dump(); fingerprint = canonical_fingerprint(values, actor.id)
        existing = self.repository.get_by_request_id(payload.client_request_id)
        if existing: return existing if existing.client_request_fingerprint == fingerprint else (_ for _ in ()).throw(InterventionConflictError())
        if not self.repository.hierarchy_valid(payload.project_id, payload.environment_id, payload.mra_object_id): raise InterventionValidationError("Gerarchia non valida.")
        self._assignee(payload.assigned_user_id)
        item = Intervention(**values, created_by_user_id=actor.id, client_request_fingerprint=fingerprint)
        try:
            self.repository.add_intervention(item); self._event(item, actor, "intervention_created", from_status=None, to_status="open")
            self.audit.record_change(action=INTERVENTION_CREATED, entity_type="intervention", entity_id=item.id, before=None, after=self._snapshot(item)); self.repository.commit(); self.repository.refresh(item); return item
        except IntegrityError as exc:
            self.repository.rollback()
            existing = self.repository.get_by_request_id(payload.client_request_id)
            if existing: return existing if existing.client_request_fingerprint == fingerprint else (_ for _ in ()).throw(InterventionConflictError())
            self._failure(item.id); raise InterventionPersistenceError from exc
        except Exception as exc: self._unexpected(exc, item.id)

    def update(self, item_id, payload: InterventionUpdate, actor: User):
        item = self.get(item_id)
        if item.status in {"completed", "cancelled"}: raise InterventionConflictError
        if item.version != payload.expected_version: raise InterventionConflictError
        values = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
        if "assigned_user_id" in values:
            self._assignee(values["assigned_user_id"])
            if values["assigned_user_id"] is None and item.status in {"planned", "in_progress"}:
                raise InterventionValidationError("Lo stato corrente richiede un assegnatario.")
        before = self._snapshot(item); assignment_changed = "assigned_user_id" in values and values["assigned_user_id"] != item.assigned_user_id
        for key, value in values.items(): setattr(item, key, value)
        try:
            self.repository.flush()
            if assignment_changed: self._event(item, actor, "assignment_changed", related_entity_id=item.assigned_user_id)
            action = INTERVENTION_ASSIGNED if set(values) == {"assigned_user_id"} else INTERVENTION_UPDATED
            self.audit.record_change(action=action, entity_type="intervention", entity_id=item.id, before=before, after=self._snapshot(item)); self.repository.commit(); self.repository.refresh(item); return item
        except StaleDataError as exc: self.repository.rollback(); raise InterventionConflictError from exc
        except Exception as exc: self._unexpected(exc, item.id)

    def transition(self, item_id, payload: InterventionTransition, actor: User):
        fingerprint = canonical_fingerprint(payload.model_dump(exclude={"command_id"}), actor.id)
        item = self.repository.get(item_id, lock=True)
        if item is None: raise InterventionNotFoundError
        prior = self.repository.get_command(payload.command_id)
        if prior:
            if prior.intervention_id == item.id and prior.command_fingerprint == fingerprint: return self._transition_result(prior)
            raise InterventionConflictError
        if item.version != payload.expected_version: raise InterventionConflictError
        if (payload.to_status == "cancelled" or (item.status == "completed" and payload.to_status == "in_progress")) and actor.role != "admin":
            raise InterventionPermissionError
        assignee = self.repository.get_user(item.assigned_user_id) if item.assigned_user_id else None
        try: result = apply_transition(current=item.status, target=payload.to_status, role=actor.role, has_active_assignee=bool(assignee and assignee.is_active and assignee.role in {"editor", "admin"}), note=payload.note, resolution_summary=payload.resolution_summary, started_at=item.started_at, current_resolution=item.resolution_summary)
        except InvalidTransitionError as exc: raise InterventionConflictError from exc
        before = self._snapshot(item); previous = item.status; item.status = payload.to_status; item.started_at = result.started_at; item.completed_at = result.completed_at; item.cancelled_at = result.cancelled_at; item.resolution_summary = result.resolution_summary
        try:
            self.repository.flush(); event = self._event(item, actor, result.event_type, from_status=previous, to_status=item.status, note=payload.note, resolution_summary_snapshot=result.resolution_summary_snapshot, command_id=payload.command_id, command_fingerprint=fingerprint, result_version=item.version, result_started_at=item.started_at, result_completed_at=item.completed_at, result_cancelled_at=item.cancelled_at)
            action = INTERVENTION_REOPENED if result.event_type == "reopened" else INTERVENTION_CANCELLED if item.status == "cancelled" else INTERVENTION_STATUS_CHANGED
            self.audit.record_change(action=action, entity_type="intervention", entity_id=item.id, before=before, after=self._snapshot(item)); self.repository.commit(); return self._transition_result(event)
        except IntegrityError as exc:
            self.repository.rollback(); prior = self.repository.get_command(payload.command_id)
            if prior and prior.intervention_id == item_id and prior.command_fingerprint == fingerprint: return self._transition_result(prior)
            if prior: raise InterventionConflictError from exc
            self._failure(item.id); raise InterventionPersistenceError from exc
        except Exception as exc: self._unexpected(exc, item.id)

    def timeline(self, item_id): self.get(item_id); return self.repository.timeline(item_id)
    def knowledge(self, item_id): self.get(item_id); return self.repository.knowledge(item_id)

    def link_knowledge(self, item_id, payload: InterventionKnowledgeCreate, actor: User):
        item = self.get(item_id)
        if item.status in {"completed", "cancelled"}: raise InterventionConflictError
        if not self.repository.knowledge_exists(payload.knowledge_card_id): raise KnowledgeCardNotFoundError
        link = InterventionKnowledgeLink(intervention_id=item.id, created_by_user_id=actor.id, **payload.model_dump())
        try:
            self.repository.add_knowledge_link(link); self._event(item, actor, "knowledge_linked", related_entity_id=payload.knowledge_card_id, note=payload.note or None)
            self.audit.record(action=INTERVENTION_KNOWLEDGE_LINKED, entity_type="intervention", entity_id=item.id, metadata={"usage_type": link.usage_type, "knowledge_card_id": str(link.knowledge_card_id), "link_id": str(link.id)}); self.repository.commit(); return link
        except IntegrityError as exc:
            self.repository.rollback()
            if getattr(getattr(exc, "orig", None), "diag", None) and exc.orig.diag.constraint_name == "uq_intervention_knowledge_link": raise InterventionConflictError from exc
            self._failure(item.id); raise InterventionPersistenceError from exc
        except Exception as exc: self._unexpected(exc, item.id)

    def unlink_knowledge(self, item_id, link_id, actor: User):
        item = self.get(item_id)
        if item.status in {"completed", "cancelled"}: raise InterventionConflictError
        link = self.repository.get_link(link_id)
        if link is None or link.intervention_id != item.id: raise KnowledgeCardNotFoundError
        metadata = {"usage_type": link.usage_type, "knowledge_card_id": str(link.knowledge_card_id), "link_id": str(link.id)}
        try:
            self.repository.delete_knowledge_link(link); self._event(item, actor, "knowledge_unlinked", related_entity_id=link.knowledge_card_id)
            self.audit.record(action=INTERVENTION_KNOWLEDGE_UNLINKED, entity_type="intervention", entity_id=item.id, metadata=metadata); self.repository.commit()
        except Exception as exc: self._unexpected(exc, item.id)
