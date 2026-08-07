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


class InvalidCredentialsError(Exception): pass
class AuthenticationError(Exception): pass
class UserNotFoundError(Exception): pass
class UserConflictError(Exception): pass
class LastAdminError(Exception): pass
class AuthPersistenceError(Exception): pass


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, repository: SqlAlchemyAuthRepository, passwords: PasswordService | None = None) -> None:
        self.repository = repository
        self.passwords = passwords or PasswordService()

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        now = datetime.now(UTC)
        user = self.repository.get_user_by_email(email)
        valid = self.passwords.verify(user.password_hash if user else None, password)
        if user is None or not valid or not user.is_active or (user.locked_until and user.locked_until > now):
            if user and user.is_active:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= settings.auth_max_failed_attempts:
                    user.locked_until = now + timedelta(seconds=settings.auth_lock_seconds)
                try:
                    self.repository.commit()
                except Exception as exc:
                    self.repository.rollback()
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
            self.repository.commit()
        except Exception as exc:
            self.repository.rollback()
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
            self.repository.commit()
        except Exception as exc:
            self.repository.rollback()
            raise AuthPersistenceError from exc

    def list_users(self): return self.repository.list_users()

    def create_user(self, payload: UserCreate) -> User:
        if self.repository.get_user_by_email(payload.email): raise UserConflictError
        user = User(email=payload.email, display_name=payload.display_name, password_hash=self.passwords.hash(payload.password), role=payload.role, must_change_password=payload.must_change_password)
        try:
            self.repository.add(user); self.repository.commit(); return user
        except IntegrityError as exc:
            self.repository.rollback(); raise UserConflictError from exc
        except Exception as exc:
            self.repository.rollback(); raise AuthPersistenceError from exc

    def update_user(self, user_id: uuid.UUID, payload: UserUpdate) -> User:
        user = self.repository.get_user(user_id)
        if not user: raise UserNotFoundError
        values = payload.model_dump(exclude_unset=True)
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
            self.repository.commit(); return user
        except LastAdminError:
            self.repository.rollback(); raise
        except Exception as exc:
            self.repository.rollback(); raise AuthPersistenceError from exc

    def revoke_user_sessions(self, user_id: uuid.UUID) -> None:
        if not self.repository.get_user(user_id): raise UserNotFoundError
        try:
            self.repository.revoke_user_sessions(user_id, datetime.now(UTC)); self.repository.commit()
        except Exception as exc:
            self.repository.rollback(); raise AuthPersistenceError from exc
