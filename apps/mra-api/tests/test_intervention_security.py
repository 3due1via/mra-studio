import uuid

from app.db import SessionLocal
from app.models import User
from app.services.password_service import PasswordService

ORIGIN_HEADERS = {"Origin": "http://localhost:5173", "Sec-Fetch-Site": "same-origin"}
PASSWORD = "A-secure-password-123"


def add_user(email: str, role: str, active: bool = True) -> User:
    with SessionLocal() as session:
        user = User(email=email, display_name=email.split("@")[0], password_hash=PasswordService().hash(PASSWORD), role=role, is_active=active)
        session.add(user); session.commit(); session.refresh(user); session.expunge(user); return user


def login(client, user: User) -> str:
    client.cookies.clear()
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}, headers=ORIGIN_HEADERS)
    assert response.status_code == 200
    return response.cookies["mra_csrf"]


def mutation_headers(csrf: str) -> dict[str, str]:
    return {**ORIGIN_HEADERS, "X-CSRF-Token": csrf}


def workspace(client, csrf: str):
    project = client.post("/api/v1/projects", headers=mutation_headers(csrf), json={"name":"RBAC project","project_type":"Maintenance"}).json()
    environment = client.post(f"/api/v1/projects/{project['id']}/environments", headers=mutation_headers(csrf), json={"name":"RBAC environment","environment_type":"Workshop"}).json()
    item = client.post(f"/api/v1/environments/{environment['id']}/objects", headers=mutation_headers(csrf), json={"category":"Machine","name":"RBAC object"}).json()
    return project, environment, item


def create_intervention(client, csrf, hierarchy, actor_id):
    project, environment, item = hierarchy
    response = client.post("/api/v1/interventions", headers=mutation_headers(csrf), json={"client_request_id":str(uuid.uuid4()),"project_id":project["id"],"environment_id":environment["id"],"mra_object_id":item["id"],"title":"RBAC intervention","assigned_user_id":str(actor_id)})
    assert response.status_code == 201
    return response.json()


def test_intervention_real_rbac_and_assignee_projection(app_client):
    editor = add_user("rbac-editor@example.test", "editor"); viewer = add_user("rbac-viewer@example.test", "viewer"); admin = add_user("rbac-admin@example.test", "admin"); add_user("rbac-disabled@example.test", "editor", False)
    assert app_client.get("/api/v1/interventions").status_code == 401
    editor_csrf = login(app_client, editor); hierarchy = workspace(app_client, editor_csrf); intervention = create_intervention(app_client, editor_csrf, hierarchy, editor.id)
    assignees = app_client.get("/api/v1/interventions/assignees"); assert assignees.status_code == 200
    assert all(set(value) == {"id", "display_name", "role"} and value["role"] in {"editor", "admin"} for value in assignees.json())
    viewer_csrf = login(app_client, viewer)
    for path in ("/api/v1/interventions", "/api/v1/interventions/summary", f"/api/v1/interventions/{intervention['id']}", f"/api/v1/interventions/{intervention['id']}/timeline", f"/api/v1/interventions/{intervention['id']}/knowledge"):
        assert app_client.get(path).status_code == 200
    assert app_client.get("/api/v1/interventions/assignees").status_code == 403
    assert app_client.patch(f"/api/v1/interventions/{intervention['id']}", headers=mutation_headers(viewer_csrf), json={"expected_version":intervention["version"],"title":"Denied"}).status_code == 403
    editor_csrf = login(app_client, editor)
    assert app_client.post(f"/api/v1/interventions/{intervention['id']}/transitions", headers=mutation_headers(editor_csrf), json={"command_id":str(uuid.uuid4()),"expected_version":intervention["version"],"to_status":"cancelled","note":"Cancel"}).status_code == 403
    admin_csrf = login(app_client, admin)
    assert app_client.post(f"/api/v1/interventions/{intervention['id']}/transitions", headers=mutation_headers(admin_csrf), json={"command_id":str(uuid.uuid4()),"expected_version":intervention["version"],"to_status":"cancelled","note":"Cancel"}).status_code == 200
    from app.models import AuditEvent
    import sqlalchemy as sa
    with SessionLocal() as session:
        event=session.scalar(sa.select(AuditEvent).where(AuditEvent.entity_id==uuid.UUID(intervention["id"]),AuditEvent.action=="intervention.cancelled"));assert event and event.actor_user_id==admin.id and event.actor_email_snapshot==admin.email and event.changed_fields==["cancelled_at","status","version"] and "Cancel" not in str(event.changes)


def test_intervention_csrf_origin_disabled_and_revoked_session(app_client):
    editor = add_user("security-editor@example.test", "editor"); disabled = add_user("security-disabled@example.test", "editor", False)
    assert app_client.post("/api/v1/auth/login", json={"email":disabled.email,"password":PASSWORD}, headers=ORIGIN_HEADERS).status_code == 401
    csrf = login(app_client, editor)
    assert app_client.post("/api/v1/interventions", json={}, headers=ORIGIN_HEADERS).status_code == 403
    assert app_client.post("/api/v1/interventions", json={}, headers={"Origin":"https://evil.test","Sec-Fetch-Site":"cross-site","X-CSRF-Token":csrf}).status_code == 403
    assert app_client.post("/api/v1/auth/logout", headers=mutation_headers(csrf)).status_code == 204
    assert app_client.get("/api/v1/interventions").status_code == 401
