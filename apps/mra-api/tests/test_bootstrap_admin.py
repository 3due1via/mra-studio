from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import threading
from unittest.mock import Mock

import pytest
from sqlalchemy import event, func, select

from app.db import SessionLocal
from app.models import User
from scripts import bootstrap_admin
from scripts.bootstrap_admin import ACTIVE_ADMIN_EXISTS_MESSAGE, BOOTSTRAP_ADMIN_LOCK_ID, BootstrapAdminError, create_first_admin


def test_bootstrap_success_validation_and_existing_admin(app_client):
    password = "Bootstrap-secret-123"
    created = create_first_admin(" FIRST@EXAMPLE.TEST ", "First Admin", password)
    assert created.email == "first@example.test" and created.role == "admin"
    with pytest.raises(BootstrapAdminError, match="active administrator"):
        create_first_admin("second@example.test", "Second Admin", password)
    assert password not in str(created)


def test_bootstrap_rejects_weak_password_and_invalid_email(app_client):
    with pytest.raises(BootstrapAdminError, match="invalid input"):
        create_first_admin("not-an-email", "Admin", "Bootstrap-secret-123")
    with pytest.raises(BootstrapAdminError, match="invalid input"):
        create_first_admin("admin@example.test", "Admin", "short")


@pytest.mark.parametrize(
    ("email", "display_name", "password"),
    [
        ("admin@example.test", "Admin", "x" * 11),
        ("admin@example.test", "Admin", "x" * 1025),
        ("admin@example.test", "", "x" * 12),
        ("admin@example.test", "x" * 121, "x" * 12),
        ("invalid-email", "Admin", "x" * 12),
    ],
)
def test_bootstrap_rejects_shared_validation_boundaries(email, display_name, password):
    with pytest.raises(BootstrapAdminError, match="invalid input"):
        create_first_admin(email, display_name, password)


@pytest.mark.parametrize(
    ("email", "display_name", "password", "normalized_email"),
    [
        (" twelve@EXAMPLE.TEST ", "Admin", "x" * 12, "twelve@example.test"),
        ("long-password@example.test", "Admin", "x" * 1024, "long-password@example.test"),
        ("long-name@example.test", "x" * 120, "x" * 12, "long-name@example.test"),
    ],
)
def test_bootstrap_accepts_shared_validation_boundaries(app_client, email, display_name, password, normalized_email):
    created = create_first_admin(email, display_name, password)
    assert created.email == normalized_email
    assert created.display_name == display_name.strip()


def test_bootstrap_password_confirmation_and_output(monkeypatch, capsys):
    answers = iter(["admin@example.test", "Admin"])
    secrets = iter(["Secret-password-123", "different-password"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(bootstrap_admin, "getpass", lambda _: next(secrets))
    assert bootstrap_admin.main() == 1
    output = capsys.readouterr().out
    assert "Secret-password-123" not in output and "different-password" not in output


def test_bootstrap_main_invalid_input_output_is_safe(monkeypatch, capsys):
    password = "weak"
    answers = iter(["invalid-email", "Admin"])
    secrets = iter([password, password])
    monkeypatch.setattr("sys.argv", ["bootstrap_admin.py"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(bootstrap_admin, "getpass", lambda _: next(secrets))

    try:
        exit_code = bootstrap_admin.main()
    except SystemExit as exc:
        exit_code = exc.code

    captured = capsys.readouterr()
    rendered = captured.out + captured.err
    assert exit_code != 0
    assert captured.out.strip() == "Administrator not created: invalid input."
    assert captured.err == ""
    for sensitive in (
        password,
        "$argon2",
        "token",
        "cookie",
        "postgresql",
        "mra_dev_password",
        "Traceback",
        "SQLAlchemy",
    ):
        assert sensitive not in rendered


def test_successful_bootstrap_output_is_non_sensitive(app_client, monkeypatch, capsys):
    password = "Output-secret-password-123"
    answers = iter([" OUTPUT@EXAMPLE.TEST ", "Output Admin"])
    secrets = iter([password, password])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(bootstrap_admin, "getpass", lambda _: next(secrets))
    assert bootstrap_admin.main() == 0
    captured = capsys.readouterr()
    rendered = captured.out + captured.err
    assert captured.err == ""
    for sensitive in (password, "$argon2", "mra_dev_password", "postgresql+psycopg://", "Traceback", "auth_sessions", "mra_session"):
        assert sensitive not in rendered
    assert rendered.strip() == "Administrator created."


def test_existing_admin_and_database_error_outputs_are_generic(app_client, monkeypatch, capsys):
    create_first_admin("existing@example.test", "Existing Admin", "Bootstrap-secret-123")
    answers = iter(["second@example.test", "Second Admin"])
    secrets = iter(["Second-secret-123", "Second-secret-123"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(bootstrap_admin, "getpass", lambda _: next(secrets))
    assert bootstrap_admin.main() == 1
    existing_output = capsys.readouterr().out
    assert "password" not in existing_output.lower() and "postgresql" not in existing_output.lower() and "Traceback" not in existing_output

    monkeypatch.setattr(bootstrap_admin, "create_first_admin", lambda *args, **kwargs: (_ for _ in ()).throw(BootstrapAdminError("database operation failed")))
    answers = iter(["error@example.test", "Error Admin"])
    secrets = iter(["Error-secret-123", "Error-secret-123"])
    assert bootstrap_admin.main() == 1
    database_output = capsys.readouterr().out
    assert database_output.strip() == "Administrator not created: database operation failed."


def test_concurrent_bootstrap_creates_only_one_admin(app_client):
    barrier = threading.Barrier(2)

    def create(index: int):
        barrier.wait(timeout=10)
        try:
            user = create_first_admin(f"admin-{index}@example.test", f"Admin {index}", "Bootstrap-secret-123")
            return ("success", user.email, None)
        except BootstrapAdminError as exc:
            return ("error", type(exc), str(exc))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result(timeout=20) for future in [pool.submit(create, 1), pool.submit(create, 2)]]
    successes = [result for result in results if result[0] == "success"]
    failures = [result for result in results if result[0] == "error"]
    assert len(successes) == 1
    assert failures == [("error", BootstrapAdminError, ACTIVE_ADMIN_EXISTS_MESSAGE)]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))) == 1


def test_bootstrap_waits_for_advisory_transaction_lock(app_client):
    lock_attempted = threading.Event()
    control = SessionLocal()
    control.execute(select(func.pg_advisory_xact_lock(BOOTSTRAP_ADMIN_LOCK_ID)))
    worker_session = SessionLocal()

    def observe_lock(orm_execute_state):
        if "pg_advisory_xact_lock" in str(orm_execute_state.statement):
            lock_attempted.set()

    event.listen(worker_session, "do_orm_execute", observe_lock)

    def bootstrap():
        return create_first_admin("locked-bootstrap@example.test", "Locked Bootstrap", "Bootstrap-secret-123", session_factory=lambda: worker_session).email

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(bootstrap)
            assert lock_attempted.wait(timeout=5)
            try:
                with pytest.raises(FutureTimeoutError):
                    future.result(timeout=0.25)
            finally:
                control.rollback()
            assert future.result(timeout=10) == "locked-bootstrap@example.test"
    finally:
        event.remove(worker_session, "do_orm_execute", observe_lock)
        worker_session.close()
        control.close()


def test_bootstrap_rolls_back_unexpected_commit_error(app_client):
    session = SessionLocal()
    session.commit = Mock(side_effect=RuntimeError("forced failure"))
    with pytest.raises(BootstrapAdminError, match="database operation failed"):
        create_first_admin("rollback@example.test", "Rollback Admin", "Bootstrap-secret-123", session_factory=lambda: session)
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == "rollback@example.test")) is None
