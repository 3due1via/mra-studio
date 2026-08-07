from app.db import SessionLocal
from app.models import User
from app.services.password_service import PasswordService

ORIGIN = "http://localhost:5173"
ORIGIN_HEADERS = {"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"}

def _add_user(email: str, role: str, *, active: bool = True, password: str = "A-secure-password-123") -> User:
    with SessionLocal() as db:
        user = User(email=email, display_name=email.split("@")[0], password_hash=PasswordService().hash(password), role=role, is_active=active)
        db.add(user); db.commit(); db.refresh(user); db.expunge(user); return user


def _login(client, email: str, password: str = "A-secure-password-123"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}, headers=ORIGIN_HEADERS)


def _mutation_headers(csrf: str, **extra: str):
    return {**ORIGIN_HEADERS, "X-CSRF-Token": csrf, **extra}


def test_login_current_user_logout_and_revocation(app_client):
    _add_user("admin@example.test", "admin")
    login = _login(app_client, "admin@example.test")
    assert login.status_code == 200
    assert login.cookies.get("mra_session")
    assert login.json()["user"]["role"] == "admin"
    assert app_client.get("/api/v1/auth/me").status_code == 200
    csrf = login.cookies["mra_csrf"]
    assert app_client.post("/api/v1/auth/logout", headers=_mutation_headers(csrf)).status_code == 204
    assert app_client.get("/api/v1/auth/me").status_code == 401


def test_invalid_credentials_and_disabled_user_are_generic(app_client):
    _add_user("disabled@example.test", "viewer", active=False)
    unknown = _login(app_client, "missing@example.test", "wrong")
    disabled = _login(app_client, "disabled@example.test")
    assert (unknown.status_code, unknown.json()) == (disabled.status_code, disabled.json())
    assert unknown.status_code == 401


def test_rbac_and_csrf(app_client):
    _add_user("viewer@example.test", "viewer")
    login = _login(app_client, "viewer@example.test")
    assert app_client.get("/api/v1/projects").status_code == 200
    response = app_client.post("/api/v1/projects", json={"name": "Denied", "code": "DENIED"}, headers=_mutation_headers(login.cookies["mra_csrf"]))
    assert response.status_code == 403
    assert app_client.get("/api/v1/users").status_code == 403


def test_admin_user_management_and_last_admin_guard(app_client):
    admin = _add_user("admin@example.test", "admin")
    login = _login(app_client, admin.email)
    csrf = login.cookies["mra_csrf"]
    created = app_client.post("/api/v1/users", headers=_mutation_headers(csrf), json={"email": "editor@example.test", "display_name": "Editor", "password": "Temporary-pass-123", "role": "editor"})
    assert created.status_code == 201
    assert app_client.get("/api/v1/users").status_code == 200
    demote = app_client.patch(f"/api/v1/users/{admin.id}", headers=_mutation_headers(csrf), json={"role": "viewer"})
    assert demote.status_code == 409
    disable = app_client.patch(f"/api/v1/users/{admin.id}", headers=_mutation_headers(csrf), json={"is_active": False})
    assert disable.status_code == 409


def test_csrf_is_required_for_authenticated_mutations(app_client):
    _add_user("editor@example.test", "editor")
    assert _login(app_client, "editor@example.test").status_code == 200
    assert app_client.post("/api/v1/projects", json={"name": "Denied", "code": "DENIED"}, headers=ORIGIN_HEADERS).status_code == 403


def test_login_origin_referer_and_fetch_metadata(app_client):
    _add_user("origin@example.test", "viewer")
    payload = {"email": "origin@example.test", "password": "A-secure-password-123"}
    assert app_client.post("/api/v1/auth/login", json=payload).status_code == 403
    assert app_client.post("/api/v1/auth/login", json=payload, headers={"Origin": "null"}).status_code == 403
    assert app_client.post("/api/v1/auth/login", json=payload, headers={"Origin": "http://localhost:5173.evil.test"}).status_code == 403
    assert app_client.post("/api/v1/auth/login", json=payload, headers={"Referer": f"{ORIGIN}/login"}).status_code == 200
    assert app_client.post("/api/v1/auth/login", json=payload, headers={"Referer": "http://localhost:5173.evil.test/login"}).status_code == 403
    assert app_client.post("/api/v1/auth/login", json=payload, headers={"Origin": ORIGIN, "Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert app_client.post("/api/v1/auth/login", content='{"email":"origin@example.test","password":"A-secure-password-123"}', headers={**ORIGIN_HEADERS, "Content-Type": "text/plain"}).status_code == 422


def test_csrf_wrong_foreign_origin_referer_and_cross_site(app_client):
    _add_user("editor-one@example.test", "editor")
    one_login = _login(app_client, "editor-one@example.test")
    one_csrf = one_login.cookies["mra_csrf"]
    app_client.cookies.clear()
    _add_user("editor-two@example.test", "editor")
    two_login = _login(app_client, "editor-two@example.test")
    two_csrf = two_login.cookies["mra_csrf"]
    payload = {"name": "Secured", "project_type": "Test"}
    assert app_client.post("/api/v1/projects", json=payload, headers=_mutation_headers("wrong-token")).status_code == 403
    assert app_client.post("/api/v1/projects", json=payload, headers=_mutation_headers(one_csrf)).status_code == 403
    assert app_client.post("/api/v1/projects", json=payload, headers={"X-CSRF-Token": two_csrf}).status_code == 403
    assert app_client.post("/api/v1/projects", json=payload, headers={"Referer": f"{ORIGIN}/projects", "X-CSRF-Token": two_csrf}).status_code == 201
    assert app_client.post("/api/v1/projects", json=payload, headers=_mutation_headers(two_csrf, Origin="https://evil.test")).status_code == 403
    assert app_client.post("/api/v1/projects", json=payload, headers=_mutation_headers(two_csrf, **{"Sec-Fetch-Site": "cross-site"})).status_code == 403


def test_wrong_password_locked_user_and_success_reset(app_client):
    user = _add_user("locked@example.test", "viewer")
    assert _login(app_client, user.email, "wrong-password").status_code == 401
    with SessionLocal() as db:
        stored = db.get(User, user.id); stored.failed_login_attempts = 4; db.commit()
    assert _login(app_client, user.email, "wrong-password").status_code == 401
    assert _login(app_client, user.email).status_code == 401
    with SessionLocal() as db:
        stored = db.get(User, user.id); stored.locked_until = None; db.commit()
    assert _login(app_client, user.email).status_code == 200
    with SessionLocal() as db:
        stored = db.get(User, user.id); assert stored.failed_login_attempts == 0; assert stored.locked_until is None
