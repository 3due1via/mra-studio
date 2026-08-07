import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import AuthSession, User

ADMIN_INVARIANT_LOCK_ID = 4_603_003_001


class SqlAlchemyAuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def get_user(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def list_users(self) -> Sequence[User]:
        return tuple(self.db.scalars(select(User).order_by(User.created_at)).all())

    def active_admin_count(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))) or 0)

    def lock_admin_invariant(self) -> None:
        self.db.execute(select(func.pg_advisory_xact_lock(ADMIN_INVARIANT_LOCK_ID)))

    def get_session(self, token_hash: str) -> AuthSession | None:
        return self.db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))

    def add(self, entity: User | AuthSession) -> None:
        self.db.add(entity)
        self.db.flush()

    def revoke_user_sessions(self, user_id: uuid.UUID, now: datetime) -> None:
        self.db.execute(update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)).values(revoked_at=now))

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
