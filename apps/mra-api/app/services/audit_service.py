import base64
import json
import uuid
import hashlib
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any

from app.audit_context import AuditRequestContext
from app.audit_sanitizer import build_audit_diff, sanitize_json_field
from app.models import AuditEvent, User
from app.repositories.audit_repository import AuditRepositoryProtocol

AUTH_LOGIN_SUCCEEDED = "auth.login.succeeded"
AUTH_LOGIN_FAILED = "auth.login.failed"
AUTH_ACCOUNT_LOCKED = "auth.account.locked"
AUTH_LOGOUT_SUCCEEDED = "auth.logout.succeeded"
USER_CREATED = "user.created"
USER_UPDATED = "user.updated"
USER_ROLE_CHANGED = "user.role.changed"
USER_ACTIVATED = "user.activated"
USER_DEACTIVATED = "user.deactivated"
USER_PASSWORD_CHANGED = "user.password.changed"
USER_SESSIONS_REVOKED = "user.sessions.revoked"
KNOWLEDGE_CARD_CREATED = "knowledge_card.created"
KNOWLEDGE_CARD_UPDATED = "knowledge_card.updated"
KNOWLEDGE_CARD_DELETED = "knowledge_card.deleted"
KNOWLEDGE_REVISION_RESTORED = "knowledge_revision.restored"
KNOWLEDGE_RELATION_CREATED = "knowledge_relation.created"
KNOWLEDGE_RELATION_DELETED = "knowledge_relation.deleted"
PROJECT_CREATED = "project.created"
PROJECT_UPDATED = "project.updated"
PROJECT_DELETED = "project.deleted"
ENVIRONMENT_CREATED = "environment.created"
ENVIRONMENT_UPDATED = "environment.updated"
ENVIRONMENT_DELETED = "environment.deleted"
MRA_OBJECT_CREATED = "mra_object.created"
MRA_OBJECT_UPDATED = "mra_object.updated"
MRA_OBJECT_DELETED = "mra_object.deleted"
OPERATION_FAILED = "operation.failed"

AUDIT_ACTIONS = frozenset(
    value
    for name, value in globals().items()
    if name.isupper() and isinstance(value, str) and ("." in value)
)
FAILURE_CODES = frozenset({"persistence_error", "audit_write_error"})


class AuditCursorError(ValueError):
    pass


class AuditEventNotFoundError(Exception):
    pass


class AuditUnavailableError(Exception):
    pass


def _filter_signature(filters: Mapping[str, Any]) -> str:
    canonical = {
        key: value.isoformat() if isinstance(value, datetime) else str(value)
        for key, value in sorted(filters.items())
        if value is not None
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:24]


def encode_cursor(event: AuditEvent, filter_signature: str = "") -> str:
    payload = json.dumps([event.occurred_at.isoformat(), str(event.id), filter_signature], separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_cursor(value: str) -> tuple[datetime, uuid.UUID, str]:
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.b64decode(padded, altchars=b"-_", validate=True)
        parsed = json.loads(raw)
        if not isinstance(parsed, list) or len(parsed) != 3 or not isinstance(parsed[2], str):
            raise ValueError
        timestamp = datetime.fromisoformat(parsed[0])
        if timestamp.tzinfo is None:
            raise ValueError
        return timestamp, uuid.UUID(parsed[1]), parsed[2]
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise AuditCursorError from exc


class AuditService:
    def __init__(self, repository: AuditRepositoryProtocol, context: AuditRequestContext) -> None:
        self.repository = repository
        self.context = context

    def set_actor(self, user: User) -> None:
        self.context.set_actor(user.id, user.email)

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        outcome: str = "success",
        changed_fields: Sequence[str] | None = None,
        changes: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        actor: User | None = None,
    ) -> AuditEvent:
        if action not in AUDIT_ACTIONS:
            raise ValueError("Unknown audit action")
        if outcome not in {"success", "failure"}:
            raise ValueError("Unknown audit outcome")
        actor_user_id = actor.id if actor is not None else self.context.actor_user_id
        actor_email = actor.email.strip().lower() if actor is not None else self.context.actor_email_snapshot
        event = AuditEvent(
            actor_user_id=actor_user_id,
            actor_email_snapshot=actor_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome=outcome,
            request_id=self.context.request_id,
            changed_fields=sanitize_json_field(list(changed_fields or [])),
            changes=sanitize_json_field(dict(changes or {})),
            metadata_json=sanitize_json_field(dict(metadata or {})),
        )
        return self.repository.add(event)

    def record_change(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        before: Mapping[str, Any] | None,
        after: Mapping[str, Any] | None,
        password_changed: bool = False,
        actor: User | None = None,
    ) -> AuditEvent:
        fields, changes = build_audit_diff(
            entity_type, before, after, password_changed=password_changed
        )
        return self.record(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changed_fields=fields,
            changes=changes,
            actor=actor,
        )

    def record_failure_after_rollback(
        self,
        *,
        entity_type: str,
        entity_id: uuid.UUID | None,
        code: str,
        commit: Callable[[], None],
        rollback: Callable[[], None],
    ) -> None:
        if code not in FAILURE_CODES:
            raise ValueError("Unknown audit failure code")
        try:
            self.record(
                action=OPERATION_FAILED,
                entity_type=entity_type,
                entity_id=entity_id,
                outcome="failure",
                metadata={"code": code},
            )
            commit()
        except Exception as exc:
            rollback()
            raise AuditUnavailableError from exc

    def get(self, event_id: uuid.UUID) -> AuditEvent:
        event = self.repository.get(event_id)
        if event is None:
            raise AuditEventNotFoundError
        return event

    def list(self, *, cursor: str | None = None, limit: int = 50, **filters):
        signature = _filter_signature(filters)
        decoded = decode_cursor(cursor) if cursor else None
        if decoded is not None and decoded[2] != signature:
            raise AuditCursorError
        position = decoded[:2] if decoded is not None else None
        events = tuple(self.repository.list(cursor=position, limit=limit + 1, **filters))
        has_more = len(events) > limit
        page = events[:limit]
        next_cursor = encode_cursor(page[-1], signature) if has_more and page else None
        return page, next_cursor
