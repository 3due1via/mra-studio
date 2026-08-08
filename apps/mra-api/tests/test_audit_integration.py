import uuid
from datetime import UTC, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading

import sqlalchemy as sa
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import AuditEvent, Environment, KnowledgeCard, KnowledgeRelation, MraObject, Project, User
from app.repositories.audit_repository import SqlAlchemyAuditRepository
from app.repositories.auth_repository import SqlAlchemyAuthRepository
from app.repositories.knowledge_relation_repository import SqlAlchemyKnowledgeRelationRepository
from app.repositories.knowledge_repository import SqlAlchemyKnowledgeRepository
from app.services.password_service import PasswordService
from app.services.auth_service import AuthService, UserConflictError, _is_user_email_conflict
from app.services.knowledge_relation_service import KnowledgeRelationConflictError, KnowledgeRelationService, _is_relation_conflict
from app.schemas import KnowledgeRelationCreate, UserCreate

ORIGIN_HEADERS = {"Origin": "http://localhost:5173", "Sec-Fetch-Site": "same-origin"}
PASSWORD = "A-secure-password-123"


def _add_user(email: str, role: str) -> User:
    with SessionLocal() as db:
        user = User(email=email, display_name=email.split("@")[0], password_hash=PasswordService().hash(PASSWORD), role=role)
        db.add(user); db.commit(); db.refresh(user); db.expunge(user); return user


def _login(client, email: str, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password}, headers=ORIGIN_HEADERS)


def _assert_request_event(
    response,
    *,
    expected_action: str,
    expected_entity_type: str,
    expected_entity_id: str | uuid.UUID | None,
    expected_actor_id: uuid.UUID | None,
    expected_actor_email: str | None,
    expected_outcome: str,
    expected_request_id: uuid.UUID,
    expected_changed_fields: list[str],
    expected_changes: dict,
    expected_metadata: dict,
    expected_event_count: int,
) -> AuditEvent:
    assert uuid.UUID(response.headers["X-Request-ID"]) == expected_request_id
    with SessionLocal() as db:
        events = tuple(db.scalars(sa.select(AuditEvent).where(AuditEvent.request_id == expected_request_id)))
        assert len(events) == expected_event_count
        event = events[0]
        assert event.action == expected_action
        assert event.entity_type == expected_entity_type
        assert event.entity_id == (uuid.UUID(str(expected_entity_id)) if expected_entity_id is not None else None)
        assert event.actor_user_id == expected_actor_id
        assert event.actor_email_snapshot == expected_actor_email
        assert event.outcome == expected_outcome
        assert event.request_id == expected_request_id
        assert event.changed_fields == expected_changed_fields
        assert event.changes == expected_changes
        assert event.metadata_json == expected_metadata
        assert isinstance(event.changed_fields, list) and isinstance(event.changes, dict)
        serialized = str({"changed_fields": event.changed_fields, "changes": event.changes, "metadata_json": event.metadata_json}).lower()
        assert not any(key in serialized for key in ("password_hash", "session_token", "csrf_token", "authorization", "database_url", "sqlalchemy_url", "$argon2"))
        return event


def _request_id(response) -> uuid.UUID:
    return uuid.UUID(response.headers["X-Request-ID"])


def test_login_attribution_anonymous_failure_and_request_id(app_client):
    user = _add_user("audit-admin@example.test", "admin")
    failed = _login(app_client, "unknown@example.test", "wrong")
    succeeded = _login(app_client, user.email)
    assert failed.status_code == 401 and succeeded.status_code == 200
    assert uuid.UUID(succeeded.headers["X-Request-ID"])
    with SessionLocal() as db:
        events = tuple(db.scalars(sa.select(AuditEvent).order_by(AuditEvent.occurred_at)))
        anonymous = next(event for event in events if event.action == "auth.login.failed")
        success = next(event for event in events if event.action == "auth.login.succeeded")
        assert anonymous.actor_user_id is None and anonymous.actor_email_snapshot is None and anonymous.entity_id is None
        assert success.actor_user_id == user.id and success.actor_email_snapshot == user.email
        assert success.request_id == uuid.UUID(succeeded.headers["X-Request-ID"])


def test_domain_mutation_and_audit_event_commit_together(app_client):
    admin = _add_user("workspace-admin@example.test", "admin")
    login = _login(app_client, admin.email); csrf = login.cookies["mra_csrf"]
    response = app_client.post("/api/v1/projects", json={"name": "Audited", "project_type": "Test"}, headers={**ORIGIN_HEADERS, "X-CSRF-Token": csrf})
    assert response.status_code == 201
    project_id = uuid.UUID(response.json()["id"])
    with SessionLocal() as db:
        events = tuple(db.scalars(sa.select(AuditEvent).where(AuditEvent.action == "project.created")))
        assert len(events) == 1
        assert events[0].entity_id == project_id and events[0].actor_user_id == admin.id


def test_audit_endpoints_are_admin_only_and_read_only(app_client):
    viewer = _add_user("audit-viewer@example.test", "viewer")
    _login(app_client, viewer.email)
    assert app_client.get("/api/v1/audit-events").status_code == 403
    app_client.cookies.clear()
    admin = _add_user("audit-reader@example.test", "admin")
    _login(app_client, admin.email)
    listing = app_client.get("/api/v1/audit-events?limit=1")
    assert listing.status_code == 200 and len(listing.json()["items"]) == 1
    event_id = listing.json()["items"][0]["id"]
    assert app_client.get(f"/api/v1/audit-events/{event_id}").status_code == 200
    for method in ("post", "put", "patch", "delete"):
        assert getattr(app_client, method)("/api/v1/audit-events").status_code == 405


def test_audit_filters_and_keyset_with_identical_timestamps(app_client):
    admin = _add_user("pagination-admin@example.test", "admin")
    _login(app_client, admin.email)
    same_time = datetime(2026, 8, 8, tzinfo=UTC)
    with SessionLocal() as db:
        for index in range(3):
            db.add(AuditEvent(occurred_at=same_time, actor_user_id=admin.id, actor_email_snapshot=admin.email, action="project.updated", entity_type="project", entity_id=uuid.uuid4(), outcome="success", request_id=uuid.uuid4(), metadata_json={"code": f"safe-{index}"}))
        db.commit()
    first = app_client.get("/api/v1/audit-events?action=project.updated&outcome=success&limit=2")
    assert first.status_code == 200 and len(first.json()["items"]) == 2 and first.json()["next_cursor"]
    with SessionLocal() as db:
        concurrent = AuditEvent(occurred_at=same_time + timedelta(days=1), actor_user_id=admin.id, actor_email_snapshot=admin.email, action="project.updated", entity_type="project", entity_id=uuid.uuid4(), outcome="success", request_id=uuid.uuid4())
        db.add(concurrent); db.commit(); concurrent_id = str(concurrent.id)
    second = app_client.get("/api/v1/audit-events", params={"action": "project.updated", "outcome": "success", "limit": 2, "cursor": first.json()["next_cursor"]})
    ids = [item["id"] for item in first.json()["items"] + second.json()["items"]]
    assert len(ids) == 3 and len(set(ids)) == 3 and concurrent_id not in ids
    assert app_client.get("/api/v1/audit-events?cursor=malformed").status_code == 422


@pytest.mark.parametrize("case,success_action", [
    ("user_create", "user.created"),
    ("relation_create", "knowledge_relation.created"),
    ("project_create", "project.created"),
    ("knowledge_update", "knowledge_card.updated"),
    ("object_delete", "mra_object.deleted"),
])
def test_success_audit_failure_rolls_back_domain_and_records_failure(app_client, monkeypatch, case, success_action):
    admin = _add_user(f"atomic-{case}@example.test", "admin")
    login = _login(app_client, admin.email); headers = {**ORIGIN_HEADERS, "X-CSRF-Token": login.cookies["mra_csrf"]}
    ids: dict[str, uuid.UUID] = {}
    with SessionLocal() as db:
        if case == "relation_create":
            source = KnowledgeCard(code="ATOMIC-SOURCE", title="Source", category="Test")
            target = KnowledgeCard(code="ATOMIC-TARGET", title="Target", category="Test")
            db.add_all([source, target]); db.commit(); ids.update(source=source.id, target=target.id)
        elif case == "knowledge_update":
            card = KnowledgeCard(code="ATOMIC-CARD", title="Before", category="Test")
            db.add(card); db.commit(); ids["card"] = card.id
        elif case == "object_delete":
            project = Project(name="Atomic", project_type="Test")
            db.add(project); db.flush()
            environment = Environment(project_id=project.id, name="Atomic env", environment_type="Test")
            db.add(environment); db.flush()
            item = MraObject(environment_id=environment.id, category="Test", name="Atomic object")
            db.add(item); db.commit(); ids["object"] = item.id
    original_add = SqlAlchemyAuditRepository.add
    postgres_failures: list[tuple[str | None, bool]] = []
    def fail_success(self, event):
        if event.action != "operation.failed":
            event.outcome = "invalid-test-outcome"
            try:
                return original_add(self, event)
            except sa.exc.IntegrityError as exc:
                postgres_failures.append((exc.orig.diag.constraint_name, not self.db.is_active))
                raise
        return original_add(self, event)
    monkeypatch.setattr(SqlAlchemyAuditRepository, "add", fail_success)
    if case == "user_create":
        response = app_client.post("/api/v1/users", headers=headers, json={"email": "rolled-back@example.test", "display_name": "Rollback", "password": "Temporary-pass-123", "role": "viewer"})
    elif case == "relation_create":
        response = app_client.post(f"/api/v1/knowledge-cards/{ids['source']}/relations", headers=headers, json={"target_id": str(ids["target"]), "relation_type": "related_to"})
    elif case == "project_create":
        response = app_client.post("/api/v1/projects", headers=headers, json={"name": "Rolled back", "project_type": "Test"})
    elif case == "knowledge_update":
        response = app_client.put(f"/api/v1/knowledge-cards/{ids['card']}", headers=headers, json={"title": "After"})
    else:
        response = app_client.delete(f"/api/v1/objects/{ids['object']}", headers=headers)
    assert response.status_code == 500
    assert postgres_failures == [("ck_audit_events_outcome", True)]
    serialized = response.text.lower()
    assert not any(secret in serialized for secret in ("password", "sql", "traceback", "token"))
    with SessionLocal() as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(AuditEvent.action == success_action)) == 0
        failures = tuple(db.scalars(sa.select(AuditEvent).where(AuditEvent.action == "operation.failed")))
        assert len(failures) == 1 and failures[0].outcome == "failure" and failures[0].metadata_json == {"code": "persistence_error"}
        assert "sensitive" not in str(failures[0].metadata_json).lower()
        if case == "user_create": assert db.scalar(sa.select(User).where(User.email == "rolled-back@example.test")) is None
        elif case == "relation_create": assert db.scalar(sa.select(sa.func.count()).select_from(KnowledgeRelation)) == 0
        elif case == "project_create": assert db.scalar(sa.select(Project).where(Project.name == "Rolled back")) is None
        elif case == "knowledge_update": assert db.get(KnowledgeCard, ids["card"]).title == "Before"
        else: assert db.get(MraObject, ids["object"]) is not None


def test_failure_audit_unavailable_returns_generic_503_without_partial_state(app_client, monkeypatch):
    admin = _add_user("atomic-503@example.test", "admin")
    login = _login(app_client, admin.email); headers = {**ORIGIN_HEADERS, "X-CSRF-Token": login.cookies["mra_csrf"]}
    attempts: list[tuple[str | None, bool]] = []
    original_add = SqlAlchemyAuditRepository.add
    def always_fail(self, event):
        event.outcome = "invalid-test-outcome"
        try:
            return original_add(self, event)
        except sa.exc.IntegrityError as exc:
            attempts.append((exc.orig.diag.constraint_name, not self.db.is_active))
            raise
    monkeypatch.setattr(SqlAlchemyAuditRepository, "add", always_fail)
    response = app_client.post("/api/v1/projects", headers=headers, json={"name": "Never committed", "project_type": "Test"})
    assert response.status_code == 503 and response.json() == {"detail": "Servizio temporaneamente non disponibile."}
    assert attempts == [("ck_audit_events_outcome", True), ("ck_audit_events_outcome", True)]
    with SessionLocal() as db:
        assert db.scalar(sa.select(Project).where(Project.name == "Never committed")) is None
        assert db.scalar(sa.select(sa.func.count()).select_from(AuditEvent)) == 1  # login only


def test_audit_api_access_limits_not_found_and_invalid_interval(app_client):
    assert app_client.get("/api/v1/audit-events").status_code == 401
    editor = _add_user("audit-editor@example.test", "editor"); _login(app_client, editor.email)
    assert app_client.get("/api/v1/audit-events").status_code == 403
    app_client.cookies.clear(); admin = _add_user("audit-limits@example.test", "admin"); _login(app_client, admin.email)
    assert app_client.get(f"/api/v1/audit-events/{uuid.uuid4()}").status_code == 404
    for limit in (1, 50, 100): assert app_client.get("/api/v1/audit-events", params={"limit": limit}).status_code == 200
    assert app_client.get("/api/v1/audit-events?limit=101").status_code == 422
    assert app_client.get("/api/v1/audit-events?occurred_from=2026-08-09T00:00:00Z&occurred_to=2026-08-08T00:00:00Z").status_code == 422


def test_all_audit_filters_combinations_and_cursor_filter_binding(app_client):
    admin = _add_user("audit-filter@example.test", "admin"); _login(app_client, admin.email)
    now = datetime.now(UTC); entity_id = uuid.uuid4(); request_id = uuid.uuid4()
    with SessionLocal() as db:
        for index in range(3):
            db.add(AuditEvent(occurred_at=now, actor_user_id=admin.id, actor_email_snapshot=admin.email, action="project.updated", entity_type="project", entity_id=entity_id, outcome="success", request_id=request_id if index < 2 else uuid.uuid4()))
        db.commit()
    params = {"actor_user_id": str(admin.id), "action": "project.updated", "entity_type": "project", "entity_id": str(entity_id), "outcome": "success", "occurred_from": (now.replace(microsecond=0)).isoformat(), "occurred_to": now.isoformat(), "request_id": str(request_id), "limit": 1}
    first = app_client.get("/api/v1/audit-events", params=params)
    assert first.status_code == 200 and len(first.json()["items"]) == 1 and first.json()["next_cursor"]
    second = app_client.get("/api/v1/audit-events", params={**params, "cursor": first.json()["next_cursor"]})
    assert second.status_code == 200 and len(second.json()["items"]) == 1
    mismatched = app_client.get("/api/v1/audit-events", params={"action": "project.deleted", "cursor": first.json()["next_cursor"]})
    assert mismatched.status_code == 422
    no_results = app_client.get("/api/v1/audit-events", params={"action": "environment.deleted"})
    assert no_results.status_code == 200 and no_results.json() == {"items": [], "next_cursor": None}


@pytest.mark.parametrize("filter_name", ["actor_user_id", "action", "entity_type", "entity_id", "outcome", "occurred_from", "occurred_to", "request_id"])
def test_each_audit_filter_has_discriminating_rows(app_client, filter_name):
    admin = _add_user(f"filter-admin-{filter_name}@example.test", "admin"); _login(app_client, admin.email)
    actor_included = _add_user(f"filter-actor-in-{filter_name}@example.test", "viewer")
    actor_excluded = _add_user(f"filter-actor-out-{filter_name}@example.test", "viewer")
    boundary = datetime(2020, 1, 1, tzinfo=UTC) if filter_name == "occurred_to" else datetime(2030, 1, 1, tzinfo=UTC)
    included_id, excluded_id = uuid.uuid4(), uuid.uuid4()
    included = dict(id=included_id, occurred_at=boundary, actor_user_id=actor_included.id, actor_email_snapshot=actor_included.email, action="environment.updated", entity_type="environment", entity_id=uuid.uuid4(), outcome="failure", request_id=uuid.uuid4())
    excluded = dict(id=excluded_id, occurred_at=boundary, actor_user_id=actor_excluded.id, actor_email_snapshot=actor_excluded.email, action="project.updated", entity_type="project", entity_id=uuid.uuid4(), outcome="success", request_id=uuid.uuid4())
    if filter_name == "occurred_from": excluded["occurred_at"] = boundary - timedelta(microseconds=1)
    if filter_name == "occurred_to": excluded["occurred_at"] = boundary + timedelta(microseconds=1)
    with SessionLocal() as db: db.add_all([AuditEvent(**included), AuditEvent(**excluded)]); db.commit()
    value = included[filter_name] if filter_name not in {"occurred_from", "occurred_to"} else boundary
    response = app_client.get("/api/v1/audit-events", params={filter_name: str(value)})
    assert response.status_code == 200
    returned = {item["id"] for item in response.json()["items"]}
    assert str(included_id) in returned and str(excluded_id) not in returned


def test_user_and_auth_event_catalog_real_operations(app_client):
    admin = _add_user("catalog-admin@example.test", "admin")
    def check(response, action, entity_type, entity_id, fields, changes, *, outcome="success", actor_id=admin.id, actor_email=admin.email):
        return _assert_request_event(
            response,
            expected_action=action,
            expected_entity_type=entity_type,
            expected_entity_id=entity_id,
            expected_actor_id=actor_id,
            expected_actor_email=actor_email,
            expected_outcome=outcome,
            expected_request_id=_request_id(response),
            expected_changed_fields=fields,
            expected_changes=changes,
            expected_metadata={},
            expected_event_count=1,
        )
    login = _login(app_client, admin.email); check(login, "auth.login.succeeded", "auth_session", _session_id(admin.id), [], {})
    csrf = login.cookies["mra_csrf"]; headers = {**ORIGIN_HEADERS, "X-CSRF-Token": csrf}
    existing_failure = _login(app_client, admin.email, "wrong"); check(existing_failure, "auth.login.failed", "user", admin.id, [], {}, outcome="failure")
    unknown_failure = _login(app_client, "never-store-this@example.test", "wrong"); unknown = check(unknown_failure, "auth.login.failed", "user", None, [], {}, outcome="failure", actor_id=None, actor_email=None)
    assert unknown.actor_user_id is None and unknown.actor_email_snapshot is None and "never-store" not in str(unknown.metadata_json)
    with SessionLocal() as db:
        stored = db.get(User, admin.id); stored.failed_login_attempts = 4; db.commit()
    locked = _login(app_client, admin.email, "wrong"); check(locked, "auth.account.locked", "user", admin.id, [], {}, outcome="failure")
    with SessionLocal() as db:
        stored = db.get(User, admin.id); stored.failed_login_attempts = 0; stored.locked_until = None; db.commit()
    created = app_client.post("/api/v1/users", headers=headers, json={"email": "catalog-user@example.test", "display_name": "Catalog", "password": "Temporary-pass-123", "role": "viewer"})
    user_id = created.json()["id"]
    check(created, "user.created", "user", user_id, ["display_name", "email", "is_active", "role"], {
        "display_name": {"before": None, "after": "Catalog"},
        "email": {"before": None, "after": "catalog-user@example.test"},
        "is_active": {"before": None, "after": True},
        "role": {"before": None, "after": "viewer"},
    })
    updates = (
        ({"display_name": "Catalog updated"}, "user.updated", "display_name", {"display_name": {"before": "Catalog", "after": "Catalog updated"}}),
        ({"role": "editor"}, "user.role.changed", "role", {"role": {"before": "viewer", "after": "editor"}}),
        ({"is_active": False}, "user.deactivated", "is_active", {"is_active": {"before": True, "after": False}}),
        ({"is_active": True}, "user.activated", "is_active", {"is_active": {"before": False, "after": True}}),
        ({"password": "A-new-secure-password-123"}, "user.password.changed", "password", {}),
    )
    for payload, action, field, expected_changes in updates:
        response = app_client.patch(f"/api/v1/users/{user_id}", headers=headers, json=payload); event = check(response, action, "user", user_id, [field], expected_changes)
        if "password" in payload: assert event.changed_fields == ["password"] and event.changes == {}
    revoked = app_client.post(f"/api/v1/users/{user_id}/revoke-sessions", headers=headers); check(revoked, "user.sessions.revoked", "user", user_id, [], {})
    second_admin = app_client.post("/api/v1/users", headers=headers, json={"email": "second-admin@example.test", "display_name": "Second admin", "password": "Temporary-pass-123", "role": "admin"})
    second_admin_id = second_admin.json()["id"]
    check(second_admin, "user.created", "user", second_admin_id, ["display_name", "email", "is_active", "role"], {
        "display_name": {"before": None, "after": "Second admin"},
        "email": {"before": None, "after": "second-admin@example.test"},
        "is_active": {"before": None, "after": True},
        "role": {"before": None, "after": "admin"},
    })
    admin_password = app_client.patch(f"/api/v1/users/{second_admin_id}", headers=headers, json={"password": "Another-secure-password-123"}); admin_password_event = check(admin_password, "user.password.changed", "user", second_admin_id, ["password"], {})
    assert admin_password_event.changed_fields == ["password"] and admin_password_event.changes == {}
    sensitive_output = (admin_password.text + str(admin_password_event.changed_fields) + str(admin_password_event.changes) + str(admin_password_event.metadata_json)).lower()
    assert not any(value in sensitive_output for value in ("another-secure", "$argon2", "csrf", "authorization", "database_url"))
    logout = app_client.post("/api/v1/auth/logout", headers=headers); check(logout, "auth.logout.succeeded", "auth_session", _latest_revoked_session_id(admin.id), [], {})


def _session_id(user_id: uuid.UUID) -> uuid.UUID:
    from app.models import AuthSession
    with SessionLocal() as db: return db.scalar(sa.select(AuthSession.id).where(AuthSession.user_id == user_id).order_by(AuthSession.created_at.desc()))


def _latest_revoked_session_id(user_id: uuid.UUID) -> uuid.UUID:
    return _session_id(user_id)


def _project_create_contract(name: str) -> dict:
    return {
        "customer": {"before": None, "after": ""},
        "name": {"before": None, "after": name},
        "progress": {"before": None, "after": 0},
        "project_type": {"before": None, "after": "Test"},
        "status": {"before": None, "after": "draft"},
        "description": {"before_length": 0, "after_length": 10},
    }


def _create_contract_test_project(app_client, email: str):
    actor = _add_user(email, "admin")
    login = _login(app_client, actor.email)
    response = app_client.post(
        "/api/v1/projects",
        headers={**ORIGIN_HEADERS, "X-CSRF-Token": login.cookies["mra_csrf"]},
        json={"name": "Contract project", "project_type": "Test", "description": "0123456789"},
    )
    assert response.status_code == 201
    return actor, response, response.json()["id"]


def test_event_contract_rejects_wrong_actor_id(app_client):
    actor, response, project_id = _create_contract_test_project(app_client, "contract-actor-a@example.test")
    wrong_actor = _add_user("contract-actor-b@example.test", "viewer")
    with pytest.raises(AssertionError):
        _assert_request_event(
            response,
            expected_action="project.created",
            expected_entity_type="project",
            expected_entity_id=project_id,
            expected_actor_id=wrong_actor.id,
            expected_actor_email=actor.email,
            expected_outcome="success",
            expected_request_id=_request_id(response),
            expected_changed_fields=["customer", "name", "progress", "project_type", "status", "description"],
            expected_changes=_project_create_contract("Contract project"),
            expected_metadata={},
            expected_event_count=1,
        )


def test_event_contract_rejects_wrong_actor_email_snapshot(app_client):
    actor, response, project_id = _create_contract_test_project(app_client, "contract-snapshot@example.test")
    with pytest.raises(AssertionError):
        _assert_request_event(
            response,
            expected_action="project.created",
            expected_entity_type="project",
            expected_entity_id=project_id,
            expected_actor_id=actor.id,
            expected_actor_email="wrong-snapshot@example.test",
            expected_outcome="success",
            expected_request_id=_request_id(response),
            expected_changed_fields=["customer", "name", "progress", "project_type", "status", "description"],
            expected_changes=_project_create_contract("Contract project"),
            expected_metadata={},
            expected_event_count=1,
        )


@pytest.mark.parametrize("mismatch", ["before", "after", "length", "extra", "missing"])
def test_event_contract_rejects_inexact_changes(app_client, mismatch):
    actor, response, project_id = _create_contract_test_project(app_client, f"contract-changes-{mismatch}@example.test")
    expected_changes = _project_create_contract("Contract project")
    if mismatch == "before":
        expected_changes["name"] = {"before": "unexpected", "after": "Contract project"}
    elif mismatch == "after":
        expected_changes["name"] = {"before": None, "after": "Wrong project"}
    elif mismatch == "length":
        expected_changes["description"] = {"before_length": 0, "after_length": 9}
    elif mismatch == "extra":
        expected_changes["unexpected"] = {"before": None, "after": "extra"}
    else:
        del expected_changes["name"]
    with pytest.raises(AssertionError):
        _assert_request_event(
            response,
            expected_action="project.created",
            expected_entity_type="project",
            expected_entity_id=project_id,
            expected_actor_id=actor.id,
            expected_actor_email=actor.email,
            expected_outcome="success",
            expected_request_id=_request_id(response),
            expected_changed_fields=["customer", "name", "progress", "project_type", "status", "description"],
            expected_changes=expected_changes,
            expected_metadata={},
            expected_event_count=1,
        )


def test_workspace_event_catalog_and_deleted_events_remain_readable(app_client):
    admin = _add_user("workspace-catalog@example.test", "admin"); login = _login(app_client, admin.email)
    headers = {**ORIGIN_HEADERS, "X-CSRF-Token": login.cookies["mra_csrf"]}
    def check(response, action, entity_type, entity_id, fields, changes):
        return _assert_request_event(
            response,
            expected_action=action,
            expected_entity_type=entity_type,
            expected_entity_id=entity_id,
            expected_actor_id=admin.id,
            expected_actor_email=admin.email,
            expected_outcome="success",
            expected_request_id=_request_id(response),
            expected_changed_fields=fields,
            expected_changes=changes,
            expected_metadata={},
            expected_event_count=1,
        )
    project_fields = ["customer", "name", "progress", "project_type", "status", "description"]
    environment_fields = ["area_m2", "environment_type", "height_m", "length_m", "name", "project_id", "width_m", "notes"]
    object_fields = ["brand", "category", "environment_id", "model", "name", "serial_number", "status", "description", "metadata_json"]
    project = app_client.post("/api/v1/projects", headers=headers, json={"name": "Catalog project", "project_type": "Test"}); project_id = project.json()["id"]
    project_create_changes = {
        "customer": {"before": None, "after": ""}, "name": {"before": None, "after": "Catalog project"},
        "progress": {"before": None, "after": 0}, "project_type": {"before": None, "after": "Test"},
        "status": {"before": None, "after": "draft"}, "description": {"before_length": 0, "after_length": 0},
    }
    check(project, "project.created", "project", project_id, project_fields, project_create_changes)
    updated_project = app_client.put(f"/api/v1/projects/{project_id}", headers=headers, json={"status": "active"}); check(updated_project, "project.updated", "project", project_id, ["status"], {"status": {"before": "draft", "after": "active"}})
    environment = app_client.post(f"/api/v1/projects/{project_id}/environments", headers=headers, json={"name": "Catalog environment", "environment_type": "Test"}); environment_id = environment.json()["id"]
    environment_create_changes = {
        "area_m2": {"before": None, "after": ""}, "environment_type": {"before": None, "after": "Test"},
        "height_m": {"before": None, "after": ""}, "length_m": {"before": None, "after": ""},
        "name": {"before": None, "after": "Catalog environment"}, "project_id": {"before": None, "after": project_id},
        "width_m": {"before": None, "after": ""}, "notes": {"before_length": 0, "after_length": 0},
    }
    check(environment, "environment.created", "environment", environment_id, environment_fields, environment_create_changes)
    updated_environment = app_client.put(f"/api/v1/environments/{environment_id}", headers=headers, json={"notes": "long notes"}); check(updated_environment, "environment.updated", "environment", environment_id, ["notes"], {"notes": {"before_length": 0, "after_length": 10}})
    item = app_client.post(f"/api/v1/environments/{environment_id}/objects", headers=headers, json={"category": "Test", "name": "Catalog object"}); object_id = item.json()["id"]
    object_create_changes = {
        "brand": {"before": None, "after": ""}, "category": {"before": None, "after": "Test"},
        "environment_id": {"before": None, "after": environment_id}, "model": {"before": None, "after": ""},
        "name": {"before": None, "after": "Catalog object"}, "serial_number": {"before": None, "after": ""},
        "status": {"before": None, "after": "active"}, "description": {"before_length": 0, "after_length": 0},
        "metadata_json": {"before_length": 0, "after_length": 0},
    }
    check(item, "mra_object.created", "mra_object", object_id, object_fields, object_create_changes)
    updated_item = app_client.put(f"/api/v1/objects/{object_id}", headers=headers, json={"status": "maintenance"}); check(updated_item, "mra_object.updated", "mra_object", object_id, ["status"], {"status": {"before": "active", "after": "maintenance"}})
    object_delete_changes = {
        "brand": {"before": "", "after": None}, "category": {"before": "Test", "after": None},
        "environment_id": {"before": environment_id, "after": None}, "model": {"before": "", "after": None},
        "name": {"before": "Catalog object", "after": None}, "serial_number": {"before": "", "after": None},
        "status": {"before": "maintenance", "after": None}, "description": {"before_length": 0, "after_length": 0},
        "metadata_json": {"before_length": 0, "after_length": 0},
    }
    deleted_item = app_client.delete(f"/api/v1/objects/{object_id}", headers=headers); object_event = check(deleted_item, "mra_object.deleted", "mra_object", object_id, object_fields, object_delete_changes)
    assert object_event.changes and app_client.get(f"/api/v1/audit-events/{object_event.id}").status_code == 200
    item2 = app_client.post(f"/api/v1/environments/{environment_id}/objects", headers=headers, json={"category": "Test", "name": "Cascade object"})
    check(item2, "mra_object.created", "mra_object", item2.json()["id"], object_fields, {**object_create_changes, "name": {"before": None, "after": "Cascade object"}})
    environment_delete_changes = {
        "area_m2": {"before": "", "after": None}, "environment_type": {"before": "Test", "after": None},
        "height_m": {"before": "", "after": None}, "length_m": {"before": "", "after": None},
        "name": {"before": "Catalog environment", "after": None}, "project_id": {"before": project_id, "after": None},
        "width_m": {"before": "", "after": None}, "notes": {"before_length": 10, "after_length": 0},
    }
    deleted_environment = app_client.delete(f"/api/v1/environments/{environment_id}", headers=headers); environment_event = check(deleted_environment, "environment.deleted", "environment", environment_id, environment_fields, environment_delete_changes)
    assert environment_event.changes and app_client.get(f"/api/v1/audit-events/{environment_event.id}").status_code == 200
    environment2 = app_client.post(f"/api/v1/projects/{project_id}/environments", headers=headers, json={"name": "Second environment", "environment_type": "Test"})
    check(environment2, "environment.created", "environment", environment2.json()["id"], environment_fields, {**environment_create_changes, "name": {"before": None, "after": "Second environment"}})
    project_delete_changes = {
        "customer": {"before": "", "after": None}, "name": {"before": "Catalog project", "after": None},
        "progress": {"before": 0, "after": None}, "project_type": {"before": "Test", "after": None},
        "status": {"before": "active", "after": None}, "description": {"before_length": 0, "after_length": 0},
    }
    deleted_project = app_client.delete(f"/api/v1/projects/{project_id}", headers=headers); project_event = check(deleted_project, "project.deleted", "project", project_id, project_fields, project_delete_changes)
    assert project_event.changes and app_client.get(f"/api/v1/audit-events/{project_event.id}").status_code == 200


def test_knowledge_event_catalog_relations_restore_and_deleted_event(app_client):
    admin = _add_user("knowledge-catalog@example.test", "admin"); login = _login(app_client, admin.email)
    headers = {**ORIGIN_HEADERS, "X-CSRF-Token": login.cookies["mra_csrf"]}
    def check(response, action, entity_type, entity_id, fields, changes):
        return _assert_request_event(
            response,
            expected_action=action,
            expected_entity_type=entity_type,
            expected_entity_id=entity_id,
            expected_actor_id=admin.id,
            expected_actor_email=admin.email,
            expected_outcome="success",
            expected_request_id=_request_id(response),
            expected_changed_fields=fields,
            expected_changes=changes,
            expected_metadata={},
            expected_event_count=1,
        )
    card_fields = ["category", "code", "status", "title", "version", "causes", "diagnosis", "procedure", "safety", "summary", "symptoms", "tools"]
    payload = {"code": "CATALOG-ONE", "title": "Catalog one", "category": "Test", "procedure": "initial procedure"}
    card = app_client.post("/api/v1/knowledge-cards", headers=headers, json=payload); card_id = card.json()["id"]
    card_create_changes = {
        "category": {"before": None, "after": "Test"}, "code": {"before": None, "after": "CATALOG-ONE"},
        "status": {"before": None, "after": "draft"}, "title": {"before": None, "after": "Catalog one"},
        "version": {"before": None, "after": "1.0.0"}, "causes": {"before_length": 0, "after_length": 0},
        "diagnosis": {"before_length": 0, "after_length": 0}, "procedure": {"before_length": 0, "after_length": 17},
        "safety": {"before_length": 0, "after_length": 0}, "summary": {"before_length": 0, "after_length": 0},
        "symptoms": {"before_length": 0, "after_length": 0}, "tools": {"before_length": 0, "after_length": 0},
    }
    check(card, "knowledge_card.created", "knowledge_card", card_id, card_fields, card_create_changes)
    target = app_client.post("/api/v1/knowledge-cards", headers=headers, json={**payload, "code": "CATALOG-TWO", "title": "Catalog two"}); target_id = target.json()["id"]
    check(target, "knowledge_card.created", "knowledge_card", target_id, card_fields, {**card_create_changes, "code": {"before": None, "after": "CATALOG-TWO"}, "title": {"before": None, "after": "Catalog two"}})
    updated = app_client.put(f"/api/v1/knowledge-cards/{card_id}", headers=headers, json={"title": "Changed", "procedure": "a much longer procedure"}); check(updated, "knowledge_card.updated", "knowledge_card", card_id, ["title", "procedure"], {
        "title": {"before": "Catalog one", "after": "Changed"},
        "procedure": {"before_length": 17, "after_length": 23},
    })
    revisions = app_client.get(f"/api/v1/knowledge-cards/{card_id}/revisions").json(); revision_id = revisions[-1]["id"]
    restored = app_client.post(f"/api/v1/knowledge-cards/{card_id}/revisions/{revision_id}/restore", headers=headers); check(restored, "knowledge_revision.restored", "knowledge_card", card_id, ["title", "procedure"], {
        "title": {"before": "Changed", "after": "Catalog one"},
        "procedure": {"before_length": 23, "after_length": 17},
    })
    relation = app_client.post(f"/api/v1/knowledge-cards/{card_id}/relations", headers=headers, json={"target_id": target_id, "relation_type": "related_to", "note": "safe note"}); relation_id = relation.json()["id"]
    relation_create_changes = {
        "source_id": {"after": card_id}, "target_id": {"after": target_id}, "relation_type": {"after": "related_to"},
    }
    check(relation, "knowledge_relation.created", "knowledge_relation", relation_id, ["source_id", "target_id", "relation_type"], relation_create_changes)
    deleted_relation = app_client.delete(f"/api/v1/knowledge-cards/{card_id}/relations/{relation_id}", headers=headers); check(deleted_relation, "knowledge_relation.deleted", "knowledge_relation", relation_id, ["source_id", "target_id", "relation_type"], {
        "source_id": {"before": card_id}, "target_id": {"before": target_id}, "relation_type": {"before": "related_to"},
    })
    card_delete_changes = {
        "category": {"before": "Test", "after": None}, "code": {"before": "CATALOG-ONE", "after": None},
        "status": {"before": "draft", "after": None}, "title": {"before": "Catalog one", "after": None},
        "version": {"before": "1.0.0", "after": None}, "causes": {"before_length": 0, "after_length": 0},
        "diagnosis": {"before_length": 0, "after_length": 0}, "procedure": {"before_length": 17, "after_length": 0},
        "safety": {"before_length": 0, "after_length": 0}, "summary": {"before_length": 0, "after_length": 0},
        "symptoms": {"before_length": 0, "after_length": 0}, "tools": {"before_length": 0, "after_length": 0},
    }
    deleted = app_client.delete(f"/api/v1/knowledge-cards/{card_id}", headers=headers); event = check(deleted, "knowledge_card.deleted", "knowledge_card", card_id, card_fields, card_delete_changes)
    assert event.changes and app_client.get(f"/api/v1/audit-events/{event.id}").status_code == 200


def test_reads_and_ordinary_401_403_422_do_not_create_audit_events(app_client):
    viewer = _add_user("no-events-viewer@example.test", "viewer"); _login(app_client, viewer.email)
    with SessionLocal() as db: before = db.scalar(sa.select(sa.func.count()).select_from(AuditEvent))
    assert app_client.get("/api/v1/projects").status_code == 200
    assert app_client.post("/api/v1/projects", headers={**ORIGIN_HEADERS, "X-CSRF-Token": app_client.cookies["mra_csrf"]}, json={"name": "Denied", "project_type": "Test"}).status_code == 403
    app_client.cookies.clear()
    assert app_client.get("/api/v1/projects").status_code == 401
    assert app_client.post("/api/v1/auth/login", headers=ORIGIN_HEADERS, json={"email": "invalid", "password": "x"}).status_code == 422
    with SessionLocal() as db: assert db.scalar(sa.select(sa.func.count()).select_from(AuditEvent)) == before


def test_concurrent_mutations_have_distinct_actor_request_and_events(app_client):
    first_user = _add_user("concurrent-one@example.test", "editor"); second_user = _add_user("concurrent-two@example.test", "editor")
    barrier = threading.Barrier(2)
    def mutate(client: TestClient, email: str, name: str):
        login = _login(client, email); headers = {**ORIGIN_HEADERS, "X-CSRF-Token": login.cookies["mra_csrf"]}
        barrier.wait(timeout=10)
        response = client.post("/api/v1/projects", headers=headers, json={"name": name, "project_type": "Test"})
        assert response.status_code == 201
        return response.json()["id"], response.headers["X-Request-ID"]
    with TestClient(app) as first_client, TestClient(app) as second_client, ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(mutate, first_client, first_user.email, "Concurrent one"), executor.submit(mutate, second_client, second_user.email, "Concurrent two")]
        results = [future.result(timeout=20) for future in futures]
    assert len({request_id for _, request_id in results}) == 2
    with SessionLocal() as db:
        events = tuple(db.scalars(sa.select(AuditEvent).where(AuditEvent.action == "project.created", AuditEvent.entity_id.in_([uuid.UUID(item[0]) for item in results]))))
        assert len(events) == 2 and {event.actor_user_id for event in events} == {first_user.id, second_user.id}
        assert len({event.request_id for event in events}) == 2


def test_append_only_trigger_rejects_concurrent_update_and_delete(app_client):
    ids = [uuid.uuid4(), uuid.uuid4()]
    with SessionLocal() as db:
        db.add_all([AuditEvent(id=event_id, action="project.created", entity_type="project", outcome="success", request_id=uuid.uuid4()) for event_id in ids]); db.commit()
    barrier = threading.Barrier(2)
    def mutate(index: int):
        with SessionLocal() as db:
            barrier.wait(timeout=10)
            statement = sa.update(AuditEvent).where(AuditEvent.id == ids[index]).values(action="project.updated") if index == 0 else sa.delete(AuditEvent).where(AuditEvent.id == ids[index])
            with pytest.raises(sa.exc.DBAPIError): db.execute(statement); db.commit()
            db.rollback()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(mutate, index) for index in range(2)]
        for future in futures: future.result(timeout=20)
    with SessionLocal() as db: assert db.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(AuditEvent.id.in_(ids))) == 2


def test_real_postgresql_constraint_names_and_domain_classification(app_client, monkeypatch):
    existing = _add_user("real-constraint@example.test", "viewer")
    with SessionLocal() as db:
        repository = SqlAlchemyAuthRepository(db)
        monkeypatch.setattr(repository, "get_user_by_email", lambda _email: None)
        with pytest.raises(UserConflictError) as user_error:
            AuthService(repository).create_user(UserCreate(email=existing.email, display_name="Duplicate", password="Temporary-pass-123", role="viewer"))
        assert user_error.value.__cause__.orig.diag.constraint_name == "ix_users_email"
        assert _is_user_email_conflict(user_error.value.__cause__)
    with SessionLocal() as db:
        source = KnowledgeCard(code="REAL-CONSTRAINT-SOURCE", title="Source", category="Test")
        target = KnowledgeCard(code="REAL-CONSTRAINT-TARGET", title="Target", category="Test")
        db.add_all([source, target]); db.flush()
        relation = KnowledgeRelation(source_id=source.id, target_id=target.id, relation_type="related_to", note="")
        db.add(relation); db.commit(); source_id, target_id = source.id, target.id
    with SessionLocal() as db:
        relation_repository = SqlAlchemyKnowledgeRelationRepository(db)
        monkeypatch.setattr(relation_repository, "find_duplicate", lambda **_kwargs: None)
        service = KnowledgeRelationService(relation_repository, SqlAlchemyKnowledgeRepository(db))
        with pytest.raises(KnowledgeRelationConflictError) as relation_error:
            service.create_relation(source_id, KnowledgeRelationCreate(target_id=target_id, relation_type="related_to"))
        assert relation_error.value.__cause__.orig.diag.constraint_name == "uq_knowledge_relation"
        assert _is_relation_conflict(relation_error.value.__cause__)
    with SessionLocal() as db:
        invalid = AuditEvent(action="project.created", entity_type="project", outcome="not-valid", request_id=uuid.uuid4())
        db.add(invalid)
        with pytest.raises(sa.exc.IntegrityError) as other_error: db.flush()
        assert other_error.value.orig.diag.constraint_name == "ck_audit_events_outcome"
        assert not _is_user_email_conflict(other_error.value) and not _is_relation_conflict(other_error.value)
        db.rollback()
