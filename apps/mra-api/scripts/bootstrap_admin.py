"""Interactively create the first administrator without accepting a password in arguments."""

from collections.abc import Callable
from getpass import getpass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User
from app.schemas import normalize_display_name_value, normalize_email_value, validate_password_value
from app.services.password_service import PasswordService

BOOTSTRAP_ADMIN_LOCK_ID = 4_603_003_002
ACTIVE_ADMIN_EXISTS_MESSAGE = "active administrator already exists"


class BootstrapAdminError(Exception):
    pass


def create_first_admin(
    email: str,
    display_name: str,
    password: str,
    session_factory: Callable[[], Session] = SessionLocal,
) -> User:
    try:
        normalized_email = normalize_email_value(email)
    except ValueError as exc:
        raise BootstrapAdminError("invalid input") from exc
    try:
        display_name = normalize_display_name_value(display_name)
        password = validate_password_value(password)
    except ValueError as exc:
        raise BootstrapAdminError("invalid input") from exc
    with session_factory() as db:
        try:
            db.execute(select(func.pg_advisory_xact_lock(BOOTSTRAP_ADMIN_LOCK_ID)))
            if db.scalar(select(User).where(User.role == "admin", User.is_active.is_(True))):
                raise BootstrapAdminError(ACTIVE_ADMIN_EXISTS_MESSAGE)
            if db.scalar(select(User).where(func.lower(User.email) == normalized_email)):
                raise BootstrapAdminError("email already registered")
            user = User(email=normalized_email, display_name=display_name, password_hash=PasswordService().hash(password), role="admin", must_change_password=False)
            db.add(user)
            db.commit()
            db.refresh(user)
            db.expunge(user)
            return user
        except BootstrapAdminError:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise BootstrapAdminError("database operation failed") from exc


def main() -> int:
    email = input("Administrator email: ")
    display_name = input("Display name: ")
    password = getpass("Password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        print("Administrator not created: invalid input.")
        return 1
    try:
        create_first_admin(email, display_name, password)
    except BootstrapAdminError as exc:
        print(f"Administrator not created: {exc}.")
        return 1
    print("Administrator created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
