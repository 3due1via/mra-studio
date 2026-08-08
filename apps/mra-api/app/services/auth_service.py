import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models import AuthSession, User
from app.repositories.auth_repository import SqlAlchemyAuthRepository
from app.schemas import UserCreate, UserUpdate
from app.services.password_service import PasswordService
from app.services.audit_service import (
    AuditService, AUTH_ACCOUNT_LOCKED, AUTH_LOGIN_FAILED, AUTH_LOGIN_SUCCEEDED,
    AUTH_LOGOUT_SUCCEEDED, USER_ACTIVATED, USER_CREATED, USER_DEACTIVATED,
    USER_PASSWORD_CHANGED, USER_ROLE_CHANGED, USER_SESSIONS_REVOKED, USER_UPDATED,
)


class InvalidCredentialsError(Exception): pass
class AuthenticationError(Exception): pass
class UserNotFoundError(Exception): pass
class UserConflictError(Exception): pass
class LastAdminError(Exception): pass
class AuthPersistenceError(Exception): pass


def _constraint_name(exc: IntegrityError) -> str:
    return str(getattr(getattr(exc.orig, "diag", None), "constraint_name", "") or "")


def _is_user_email_conflict(exc: IntegrityError) -> bool:
    return _constraint_name(exc) == "ix_users_email"


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, repository: SqlAlchemyAuthRepository, passwords: PasswordService | None = None, audit: AuditService | None = None) -> None:
        self.repository = repository
        self.passwords = passwords or PasswordService()
        self.audit = audit

    def _failure(self, entity_type: str, entity_id: uuid.UUID | None) -> None:
        if self.audit:
            self.audit.record_failure_after_rollback(entity_type=entity_type, entity_id=entity_id, code="persistence_error", commit=self.repository.commit, rollback=self.repository.rollback)

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        now = datetime.now(UTC)
        user = self.repository.get_user_by_email(email)
        valid = self.passwords.verify(user.password_hash if user else None, password)
        if user is None or not valid or not user.is_active or (user.locked_until and user.locked_until > now):
            action = AUTH_LOGIN_FAILED
            if user and user.is_active:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= settings.auth_max_failed_attempts:
                    user.locked_until = now + timedelta(seconds=settings.auth_lock_seconds)
                    action = AUTH_ACCOUNT_LOCKED
            try:
                if self.audit:
                    self.audit.record(action=action, entity_type="user", entity_id=user.id if user else None, outcome="failure", actor=user)
                if user or self.audit:
                    self.repository.commit()
            except Exception as exc:
                self.repository.rollback()
                self._failure("user", user.id if user else None)
                raise AuthPersistenceError from exc
            raise InvalidCredentialsError
        raw_token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        session = AuthSession(user_id=user.id, token_hash=token_hash(raw_token), csrf_token_hash=token_hash(csrf), created_at=now, last_seen_at=now, expires_at=now + timedelta(seconds=settings.session_absolute_ttl_seconds))
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        if self.passwords.needs_rehash(user.password_hash):
            user.password_hash = self.passwords.hash(password)
        try:
            self.repository.add(session)
            if self.audit:
                self.audit.record(action=AUTH_LOGIN_SUCCEEDED, entity_type="auth_session", entity_id=session.id, actor=user)
            self.repository.commit()
        except Exception as exc:
            self.repository.rollback()
            self._failure("auth_session", session.id)
            raise AuthPersistenceError from exc
        return user, raw_token, csrf

    def authenticate(self, raw_token: str | None) -> AuthContext:
        if not raw_token:
            raise AuthenticationError
        now = datetime.now(UTC)
        session = self.repository.get_session(token_hash(raw_token))
        if not session or session.revoked_at or session.expires_at <= now or session.last_seen_at + timedelta(seconds=settings.session_idle_ttl_seconds) <= now or not session.user.is_active:
            raise AuthenticationError
        if session.last_seen_at + timedelta(seconds=60) < now:
            session.last_seen_at = now
            try:
                self.repository.commit()
            except Exception as exc:
                self.repository.rollback()
                raise AuthPersistenceError from exc
        return AuthContext(session.user, session)

    def logout(self, context: AuthContext) -> None:
        context.session.revoked_at = datetime.now(UTC)
        try:
            if self.audit:
                self.audit.record(action=AUTH_LOGOUT_SUCCEEDED, entity_type="auth_session", entity_id=context.session.id, actor=context.user)
            self.repository.commit()
        except Exception as exc:
            self.repository.rollback()
            self._failure("auth_session", getattr(context.session, "id", None))
            raise AuthPersistenceError from exc

    def list_users(self): return self.repository.list_users()

    def create_user(self, payload: UserCreate) -> User:
        if self.repository.get_user_by_email(payload.email): raise UserConflictError
        user = User(email=payload.email, display_name=payload.display_name, password_hash=self.passwords.hash(payload.password), role=payload.role, must_change_password=payload.must_change_password)
        try:
            self.repository.add(user)
        except IntegrityError as exc:
            self.repository.rollback()
            if _is_user_email_conflict(exc):
                raise UserConflictError from exc
            self._failure("user", user.id)
            raise AuthPersistenceError from exc
        except Exception as exc:
            self.repository.rollback(); self._failure("user", user.id); raise AuthPersistenceError from exc
        try:
            if self.audit:
                self.audit.record_change(action=USER_CREATED, entity_type="user", entity_id=user.id, before=None, after={"email": user.email, "display_name": user.display_name, "role": user.role, "is_active": user.is_active})
            self.repository.commit()
            return user
        except Exception as exc:
            self.repository.rollback(); self._failure("user", user.id); raise AuthPersistenceError from exc

    def update_user(self, user_id: uuid.UUID, payload: UserUpdate) -> User:
        user = self.repository.get_user(user_id)
        if not user: raise UserNotFoundError
        values = payload.model_dump(exclude_unset=True)
        before = {name: getattr(user, name) for name in ("email", "display_name", "role", "is_active", "must_change_password")}
        reducing_admins = user.role == "admin" and user.is_active and (values.get("role", "admin") != "admin" or values.get("is_active") is False)
        try:
            if reducing_admins:
                self.repository.lock_admin_invariant()
                if self.repository.active_admin_count() <= 1:
                    raise LastAdminError
            password = values.pop("password", None)
            for key, value in values.items(): setattr(user, key, value)
            if password:
                user.password_hash = self.passwords.hash(password)
                user.password_changed_at = datetime.now(UTC)
                self.repository.revoke_user_sessions(user.id, datetime.now(UTC))
            if self.audit:
                if password:
                    action = USER_PASSWORD_CHANGED
                elif "role" in values:
                    action = USER_ROLE_CHANGED
                elif values.get("is_active") is True:
                    action = USER_ACTIVATED
                elif values.get("is_active") is False:
                    action = USER_DEACTIVATED
                else:
                    action = USER_UPDATED
                after = {name: getattr(user, name) for name in before}
                self.audit.record_change(action=action, entity_type="user", entity_id=user.id, before=before, after=after, password_changed=bool(password))
            self.repository.commit(); return user
        except LastAdminError:
            self.repository.rollback(); raise
        except Exception as exc:
            self.repository.rollback(); self._failure("user", user.id); raise AuthPersistenceError from exc

    def revoke_user_sessions(self, user_id: uuid.UUID) -> None:
        if not self.repository.get_user(user_id): raise UserNotFoundError
        try:
            self.repository.revoke_user_sessions(user_id, datetime.now(UTC))
            if self.audit:
                self.audit.record(action=USER_SESSIONS_REVOKED, entity_type="user", entity_id=user_id)
            self.repository.commit()
        except Exception as exc:
            self.repository.rollback(); self._failure("user", user_id); raise AuthPersistenceError from exc
