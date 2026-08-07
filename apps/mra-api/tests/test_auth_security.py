from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import UTC, datetime, timedelta
import threading
import pytest

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import AuthSession, User
from app.repositories.auth_repository import ADMIN_INVARIANT_LOCK_ID, SqlAlchemyAuthRepository
from app.schemas import UserUpdate
from app.services.auth_service import AuthService, LastAdminError, token_hash
from app.services.password_service import PasswordService
ORIGIN_HEADERS = {"Origin": "http://localhost:5173", "Sec-Fetch-Site": "same-origin"}


def _add_user(email: str, role: str, *, active: bool = True, password: str = "A-secure-password-123") -> User:
    with SessionLocal() as db:
        user = User(email=email, display_name=email.split("@")[0], password_hash=PasswordService().hash(password), role=role, is_active=active)
        db.add(user); db.commit(); db.refresh(user); db.expunge(user); return user


def _login(client, email: str, password: str = "A-secure-password-123"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}, headers=ORIGIN_HEADERS)


def _mutation_headers(csrf: str):
    return {**ORIGIN_HEADERS, "X-CSRF-Token": csrf}


def _stored_session(raw_token: str) -> AuthSession:
    with SessionLocal() as db:
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(raw_token)))
        assert session is not None
        db.expunge(session)
        return session


def test_session_expiry_revocation_idle_timeout_and_absolute_limit(app_client):
    user = _add_user("session@example.test", "viewer")
    login = _login(app_client, user.email)
    raw = login.cookies["mra_session"]
    stored = _stored_session(raw)
    assert stored.expires_at - stored.created_at == timedelta(hours=12)

    with SessionLocal() as db:
        current = db.get(AuthSession, stored.id); current.last_seen_at = datetime.now(UTC) - timedelta(minutes=31); db.commit()
    assert app_client.get("/api/v1/auth/me").status_code == 401

    login = _login(app_client, user.email); raw = login.cookies["mra_session"]; stored = _stored_session(raw)
    absolute_expiry = stored.expires_at
    with SessionLocal() as db:
        current = db.get(AuthSession, stored.id); current.last_seen_at = datetime.now(UTC) - timedelta(minutes=2); db.commit()
    assert app_client.get("/api/v1/auth/me").status_code == 200
    assert _stored_session(raw).expires_at == absolute_expiry

    with SessionLocal() as db:
        current = db.get(AuthSession, stored.id); current.revoked_at = datetime.now(UTC); db.commit()
    assert app_client.get("/api/v1/auth/me").status_code == 401

    login = _login(app_client, user.email); stored = _stored_session(login.cookies["mra_session"])
    with SessionLocal() as db:
        current = db.get(AuthSession, stored.id); current.expires_at = datetime.now(UTC) - timedelta(seconds=1); db.commit()
    assert app_client.get("/api/v1/auth/me").status_code == 401


def test_cookie_attributes_and_logout_deletion(app_client):
    _add_user("cookie@example.test", "viewer")
    login = _login(app_client, "cookie@example.test")
    assert "csrf_token" not in login.json()
    cookies = login.headers.get_list("set-cookie")
    session_cookie = next(value for value in cookies if value.startswith("mra_session="))
    csrf_cookie = next(value for value in cookies if value.startswith("mra_csrf="))
    assert "HttpOnly" in session_cookie and "SameSite=lax" in session_cookie and "Path=/" in session_cookie
    assert "Secure" not in session_cookie and "Domain=" not in session_cookie
    assert "HttpOnly" not in csrf_cookie and "SameSite=lax" in csrf_cookie
    logout = app_client.post("/api/v1/auth/logout", headers=_mutation_headers(login.cookies["mra_csrf"]))
    deleted = logout.headers.get_list("set-cookie")
    assert any(value.startswith("mra_session=") and "Max-Age=0" in value and "Path=/" in value for value in deleted)
    assert any(value.startswith("mra_csrf=") and "Max-Age=0" in value and "Path=/" in value for value in deleted)


def test_anonymous_editor_viewer_admin_and_immediate_role_change(app_client):
    app_client.cookies.clear()
    assert app_client.get("/api/v1/projects").status_code == 401
    viewer = _add_user("matrix-viewer@example.test", "viewer")
    viewer_login = _login(app_client, viewer.email)
    assert app_client.get("/api/v1/projects").status_code == 200
    assert app_client.post("/api/v1/projects", json={"name": "No", "project_type": "Test"}, headers=_mutation_headers(viewer_login.cookies["mra_csrf"])).status_code == 403

    app_client.cookies.clear(); editor = _add_user("matrix-editor@example.test", "editor")
    editor_login = _login(app_client, editor.email)
    created = app_client.post("/api/v1/projects", json={"name": "Editor project", "project_type": "Test"}, headers=_mutation_headers(editor_login.cookies["mra_csrf"]))
    assert created.status_code == 201
    assert app_client.delete(f"/api/v1/projects/{created.json()['id']}", headers=_mutation_headers(editor_login.cookies["mra_csrf"])).status_code == 403

    with SessionLocal() as db:
        stored = db.get(User, editor.id); stored.role = "viewer"; db.commit()
    assert app_client.post("/api/v1/projects", json={"name": "Changed", "project_type": "Test"}, headers=_mutation_headers(editor_login.cookies["mra_csrf"])).status_code == 403

    app_client.cookies.clear(); admin = _add_user("matrix-admin@example.test", "admin")
    admin_login = _login(app_client, admin.email)
    assert app_client.delete(f"/api/v1/projects/{created.json()['id']}", headers=_mutation_headers(admin_login.cookies["mra_csrf"])).status_code == 204
    assert app_client.get("/api/v1/users").status_code == 200


def test_password_change_revokes_existing_sessions(app_client):
    admin = _add_user("password-admin@example.test", "admin")
    target = _add_user("password-user@example.test", "viewer")
    target_login = _login(app_client, target.email)
    target_raw = target_login.cookies["mra_session"]
    app_client.cookies.clear()
    admin_login = _login(app_client, admin.email)
    response = app_client.patch(f"/api/v1/users/{target.id}", json={"password": "A-new-secure-password-456"}, headers=_mutation_headers(admin_login.cookies["mra_csrf"]))
    assert response.status_code == 200
    app_client.cookies.set("mra_session", target_raw)
    assert app_client.get("/api/v1/auth/me").status_code == 401


def test_concurrent_admin_reductions_cannot_remove_last_admin(app_client):
    first = _add_user("concurrent-admin-1@example.test", "admin")
    second = _add_user("concurrent-admin-2@example.test", "admin")
    barrier = threading.Barrier(2)

    def demote(user_id):
        with SessionLocal() as db:
            service = AuthService(SqlAlchemyAuthRepository(db), PasswordService())
            barrier.wait(timeout=10)
            try:
                service.update_user(user_id, UserUpdate(role="viewer"))
                return "updated"
            except LastAdminError:
                return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(future.result(timeout=20) for future in [pool.submit(demote, first.id), pool.submit(demote, second.id)])
    assert results == ["blocked", "updated"]
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.role == "admin", User.is_active.is_(True)).limit(1)) is not None


@pytest.mark.parametrize("payload", [UserUpdate(role="viewer"), UserUpdate(is_active=False)], ids=["demotion", "disable"])
def test_admin_reduction_waits_for_advisory_transaction_lock(app_client, payload):
    case = "demotion" if payload.role is not None else "disable"
    target = _add_user(f"locked-{case}@example.test", "admin")
    _add_user("remaining-admin@example.test", "admin")
    lock_attempted = threading.Event()
    control = SessionLocal()
    control.execute(select(func.pg_advisory_xact_lock(ADMIN_INVARIANT_LOCK_ID)))

    class SignalingRepository(SqlAlchemyAuthRepository):
        def lock_admin_invariant(self) -> None:
            lock_attempted.set()
            super().lock_admin_invariant()

    def reduce_admin():
        with SessionLocal() as db:
            return AuthService(SignalingRepository(db), PasswordService()).update_user(target.id, payload).id

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(reduce_admin)
            assert lock_attempted.wait(timeout=5)
            try:
                with pytest.raises(FutureTimeoutError):
                    future.result(timeout=0.25)
            finally:
                control.rollback()
            assert future.result(timeout=10) == target.id
    finally:
        control.close()
