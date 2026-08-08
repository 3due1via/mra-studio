import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass

from fastapi import Request

_current_audit_context: ContextVar["AuditRequestContext | None"] = ContextVar("audit_request_context", default=None)


@dataclass
class AuditRequestContext:
    request_id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    actor_email_snapshot: str | None = None

    def set_actor(self, user_id: uuid.UUID, email: str) -> None:
        self.actor_user_id = user_id
        self.actor_email_snapshot = email.strip().lower()


def create_audit_context() -> AuditRequestContext:
    return AuditRequestContext(request_id=uuid.uuid4())


def bind_audit_context(context: AuditRequestContext) -> Token:
    return _current_audit_context.set(context)


def reset_audit_context(token: Token) -> None:
    _current_audit_context.reset(token)


def current_audit_context() -> AuditRequestContext | None:
    return _current_audit_context.get()


def get_request_audit_context(request: Request) -> AuditRequestContext:
    context = getattr(request.state, "audit_context", None)
    if context is None:
        context = current_audit_context() or create_audit_context()
        request.state.audit_context = context
    return context
