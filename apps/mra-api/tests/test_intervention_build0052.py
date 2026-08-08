import copy
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient


@contextmanager
def _flush_race(*, mode, target_id):
    """Synchronize only the two target ORM flushes; never touches production code."""
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    from app.db import engine
    from app.models import Intervention

    barrier = threading.Barrier(2)
    all_arrived = threading.Event()
    lock = threading.Lock()
    state = {"arrivals": [], "constraint_names": [], "rollbacks": []}

    def target_matches(session):
        values = session.new if mode == "create" else session.dirty
        matches = [value for value in values if isinstance(value, Intervention)]
        if mode == "create":
            return any(value.client_request_id == target_id for value in matches)
        return any(
            value.id == target_id
            and sa.inspect(value).attrs.assigned_user_id.history.has_changes()
            and value.version == 1
            for value in matches
        )

    def before_flush(session, _flush_context, _instances):
        if not target_matches(session):
            return
        with lock:
            arrival = (id(session), threading.get_ident())
            assert arrival not in state["arrivals"]
            state["arrivals"].append(arrival)
            if len(state["arrivals"]) == 2:
                all_arrived.set()
        barrier.wait(timeout=8)

    def handle_error(exception_context):
        diag = getattr(exception_context.original_exception, "diag", None)
        name = getattr(diag, "constraint_name", None)
        if name:
            with lock:
                state["constraint_names"].append(name)

    def after_soft_rollback(session, _previous_transaction):
        with lock:
            if id(session) in {session_id for session_id, _thread_id in state["arrivals"]}:
                state["rollbacks"].append(id(session))

    event.listen(Session, "before_flush", before_flush)
    event.listen(Session, "after_soft_rollback", after_soft_rollback)
    event.listen(engine, "handle_error", handle_error)
    try:
        yield state, all_arrived
    finally:
        event.remove(Session, "before_flush", before_flush)
        event.remove(Session, "after_soft_rollback", after_soft_rollback)
        event.remove(engine, "handle_error", handle_error)
        assert not event.contains(Session, "before_flush", before_flush)
        assert not event.contains(Session, "after_soft_rollback", after_soft_rollback)
        assert not event.contains(engine, "handle_error", handle_error)


def test_flush_race_listeners_are_removed_even_after_failure():
    with pytest.raises(RuntimeError, match="test cleanup"):
        with _flush_race(mode="create", target_id=uuid.uuid4()):
            raise RuntimeError("test cleanup")


def _frontend_guard_sources():
    frontend = Path(__file__).resolve().parents[2] / "mra-studio" / "src"
    return (
        (frontend / "auth" / "ProtectedRoute.tsx").read_text(encoding="utf-8"),
        (frontend / "App.tsx").read_text(encoding="utf-8"),
        (frontend / "pages" / "InterventionsPage.tsx").read_text(encoding="utf-8"),
    )


def test_viewer_direct_create_route_is_fail_closed():
    guard, routes, page = _frontend_guard_sources()
    assert 'canEditInterventions(user?.role) ? <Outlet /> : <Navigate to="/interventions" replace />' in guard
    assert '<Route element={<EditorRoute />}><Route path="/interventions/new"' in routes
    assert "const createMode=canEdit&&show" in page
    assert "{canEdit&&createMode&&<form" in page
    assert "enabled:createMode" in page


def test_editor_can_open_create_route():
    guard, _routes, _page = _frontend_guard_sources()
    assert 'role === "editor" || role === "admin"' in guard


def test_admin_can_open_create_route():
    guard, _routes, _page = _frontend_guard_sources()
    assert 'role === "admin"' in guard


@pytest.fixture
def intervention_client(app_client):
    from app.db import SessionLocal
    from app.dependencies import require_admin, require_csrf, require_editor, require_viewer
    from app.main import app
    from app.models import User

    actor = User(
        id=uuid.uuid4(), email="build0052-admin@example.test", display_name="Build 005.2 Admin",
        password_hash="unused", role="admin", is_active=True,
    )
    with SessionLocal() as session:
        session.add(actor)
        session.commit()
        session.refresh(actor)
        session.expunge(actor)
    for dependency in (require_viewer, require_editor, require_admin):
        app.dependency_overrides[dependency] = lambda: actor
    app.dependency_overrides[require_csrf] = lambda: None
    yield app_client, actor
    for dependency in (require_viewer, require_editor, require_admin, require_csrf):
        app.dependency_overrides.pop(dependency, None)


def _workspace(client):
    project = client.post("/api/v1/projects", json={"name": "Build 005.2", "project_type": "Maintenance"}).json()
    environment = client.post(
        f"/api/v1/projects/{project['id']}/environments",
        json={"name": "Laboratorio", "environment_type": "Workshop"},
    ).json()
    obj = client.post(
        f"/api/v1/environments/{environment['id']}/objects",
        json={"category": "Machine", "name": "Pressa"},
    ).json()
    return project, environment, obj


def _create_payload(hierarchy, request_id=None, **changes):
    project, environment, obj = hierarchy
    payload = {
        "client_request_id": str(request_id or uuid.uuid4()),
        "project_id": project["id"],
        "environment_id": environment["id"],
        "mra_object_id": obj["id"],
        "title": "Controllo pressa",
        "description": "Verifica programmata",
        "priority": "high",
        "assigned_user_id": None,
        "due_at": None,
    }
    payload.update(changes)
    return payload


def _new_user(email, role="editor"):
    from app.db import SessionLocal
    from app.models import User
    from app.services.password_service import PasswordService

    with SessionLocal() as session:
        user = User(
            email=email,
            display_name=email.split("@")[0],
            password_hash=PasswordService().hash("A-secure-password-123"),
            role=role,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def _login_client(user):
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:5173", "Sec-Fetch-Site": "same-origin"},
        json={"email": user.email, "password": "A-secure-password-123"},
    )
    assert response.status_code == 200
    csrf = response.cookies["mra_csrf"]
    return client, {
        "Origin": "http://localhost:5173",
        "Sec-Fetch-Site": "same-origin",
        "X-CSRF-Token": csrf,
    }


def _events(intervention_id, action=None):
    from app.db import SessionLocal
    from app.models import AuditEvent

    with SessionLocal() as session:
        query = sa.select(AuditEvent).where(AuditEvent.entity_id == uuid.UUID(str(intervention_id)))
        if action:
            query = query.where(AuditEvent.action == action)
        return tuple(session.scalars(query.order_by(AuditEvent.occurred_at, AuditEvent.id)).all())


def _assert_event(
    events,
    *,
    expected_action,
    expected_entity_type,
    expected_entity_id,
    expected_actor_id,
    expected_actor_email,
    expected_request_id,
    expected_outcome,
    expected_changed_fields,
    expected_changes,
    expected_metadata,
    expected_event_count,
):
    assert len(events) == expected_event_count
    event = events[0]
    assert event.action == expected_action
    assert event.entity_type == expected_entity_type
    assert event.entity_id == uuid.UUID(str(expected_entity_id))
    assert event.actor_user_id == uuid.UUID(str(expected_actor_id))
    assert event.actor_email_snapshot == expected_actor_email
    assert event.request_id == uuid.UUID(str(expected_request_id))
    assert event.outcome == expected_outcome
    assert event.changed_fields == expected_changed_fields
    assert event.changes == expected_changes
    assert event.metadata_json == expected_metadata


def test_concurrent_assignment_only_has_one_winner(intervention_client):
    client, actor = intervention_client
    hierarchy = _workspace(client)
    assignees = (_new_user("assignment-one@example.test"), _new_user("assignment-two@example.test"))
    created = client.post("/api/v1/interventions", json=_create_payload(hierarchy)).json()

    def assign(user):
        response = client.patch(
            f"/api/v1/interventions/{created['id']}",
            json={"expected_version": created["version"], "assigned_user_id": str(user.id)},
        )
        return user, response

    with _flush_race(mode="assignment", target_id=uuid.UUID(created["id"])) as (race, all_arrived):
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(assign, user) for user in assignees]
            assert all_arrived.wait(timeout=8)
            results = [future.result(timeout=15) for future in futures]

    assert len(race["arrivals"]) == 2
    assert len({session_id for session_id, _thread_id in race["arrivals"]}) == 2
    assert len({thread_id for _session_id, thread_id in race["arrivals"]}) == 2
    from app.models import Intervention
    assert sa.inspect(Intervention).version_id_col is Intervention.__table__.c.version

    assert sorted(response.status_code for _, response in results) == [200, 409]
    winner, winning_response = next(result for result in results if result[1].status_code == 200)
    loser_response = next(response for _, response in results if response.status_code == 409)
    current = client.get(f"/api/v1/interventions/{created['id']}").json()
    assert current["assigned_user_id"] == str(winner.id)
    assert current["version"] == created["version"] + 1

    from app.db import SessionLocal
    from app.models import AuditEvent, InterventionEvent

    with SessionLocal() as session:
        item_id = uuid.UUID(created["id"])
        timeline = tuple(session.scalars(sa.select(InterventionEvent).where(InterventionEvent.intervention_id == item_id, InterventionEvent.event_type == "assignment_changed")))
        assigned = tuple(session.scalars(sa.select(AuditEvent).where(AuditEvent.entity_id == item_id, AuditEvent.action == "intervention.assigned")))
        updated = tuple(session.scalars(sa.select(AuditEvent).where(AuditEvent.entity_id == item_id, AuditEvent.action == "intervention.updated")))
        assert len(timeline) == len(assigned) == 1
        assert updated == ()
        assert assigned[0].actor_user_id == actor.id
        assert assigned[0].request_id == uuid.UUID(winning_response.headers["X-Request-ID"])
        assert assigned[0].request_id != uuid.UUID(loser_response.headers["X-Request-ID"])

    # Test-only counterexample: without a version predicate PostgreSQL accepts both
    # updates, so the synchronized 200/409 assertion above depends on version_id_col.
    from app.db import engine
    row_counts = []
    connection = engine.connect()
    transaction = None
    try:
        transaction = connection.begin()
        for assignee in assignees:
            result = connection.execute(
                sa.text("UPDATE interventions SET assigned_user_id=:assignee WHERE id=:id"),
                {"assignee": assignee.id, "id": uuid.UUID(created["id"])},
            )
            row_counts.append(result.rowcount)
        assert row_counts == [1, 1]
    finally:
        if transaction is not None and transaction.is_active:
            transaction.rollback()
        connection.close()

    with SessionLocal() as session:
        persisted = session.get(Intervention, uuid.UUID(created["id"]))
        assert persisted is not None
        assert persisted.assigned_user_id == winner.id
        assert persisted.version == created["version"] + 1
        assert session.scalar(sa.select(sa.func.count()).select_from(InterventionEvent).where(InterventionEvent.intervention_id == persisted.id, InterventionEvent.event_type == "assignment_changed")) == 1
        assert session.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(AuditEvent.entity_id == persisted.id, AuditEvent.action == "intervention.assigned")) == 1
        assert session.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(AuditEvent.entity_id == persisted.id, AuditEvent.action == "intervention.updated")) == 0


def _assert_concurrent_create_same_actor(intervention_client, monkeypatch, *, different_payload):
    client, _actor = intervention_client
    hierarchy = _workspace(client)
    request_id = uuid.uuid4()
    payloads = [_create_payload(hierarchy, request_id), _create_payload(hierarchy, request_id)]
    if different_payload:
        payloads[1]["title"] = "Payload perdente"

    from app.repositories.intervention_repository import SqlAlchemyInterventionRepository
    original_get = SqlAlchemyInterventionRepository.get_by_request_id
    fetches = []

    def observed_get(repository, value):
        result = original_get(repository, value)
        if value == request_id:
            fetches.append((threading.get_ident(), result is not None))
        return result

    monkeypatch.setattr(SqlAlchemyInterventionRepository, "get_by_request_id", observed_get)

    def create(payload):
        return client.post("/api/v1/interventions", json=payload)

    with _flush_race(mode="create", target_id=request_id) as (race, all_arrived):
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(create, payload) for payload in payloads]
            assert all_arrived.wait(timeout=8)
            responses = [future.result(timeout=15) for future in futures]

    assert len(race["arrivals"]) == 2
    assert len({session_id for session_id, _thread_id in race["arrivals"]}) == 2
    assert len({thread_id for _session_id, thread_id in race["arrivals"]}) == 2
    assert race["constraint_names"] == ["uq_interventions_client_request_id"]
    assert len(set(race["rollbacks"])) == 1
    assert sum(not found for _thread_id, found in fetches) == 2
    assert sum(found for _thread_id, found in fetches) == 1

    assert sorted(response.status_code for response in responses) == ([201, 409] if different_payload else [201, 201])
    successful = [response.json() for response in responses if response.status_code == 201]
    assert len({item["id"] for item in successful}) == 1
    if not different_payload:
        assert len({item["code"] for item in successful}) == 1
        assert responses[0].json() == responses[1].json()
    else:
        winner_index = next(index for index, response in enumerate(responses) if response.status_code == 201)
        assert successful[0]["title"] == payloads[winner_index]["title"]

    from app.db import SessionLocal
    from app.models import AuditEvent, Intervention, InterventionEvent

    with SessionLocal() as session:
        rows = tuple(session.scalars(sa.select(Intervention).where(Intervention.client_request_id == request_id)))
        assert len(rows) == 1
        item_id = rows[0].id
        assert session.scalar(sa.select(sa.func.count()).select_from(InterventionEvent).where(InterventionEvent.intervention_id == item_id, InterventionEvent.event_type == "intervention_created")) == 1
        audit_events = tuple(session.scalars(sa.select(AuditEvent).where(AuditEvent.entity_id == item_id, AuditEvent.action == "intervention.created")))
        assert len(audit_events) == 1
        response_request_ids = {uuid.UUID(response.headers["X-Request-ID"]) for response in responses}
        assert audit_events[0].request_id in response_request_ids
        assert sum(audit_events[0].request_id == request_id_value for request_id_value in response_request_ids) == 1


def test_concurrent_create_request_id_same_payload_same_actor(intervention_client, monkeypatch):
    _assert_concurrent_create_same_actor(intervention_client, monkeypatch, different_payload=False)


def test_concurrent_create_request_id_different_payload_same_actor(intervention_client, monkeypatch):
    _assert_concurrent_create_same_actor(intervention_client, monkeypatch, different_payload=True)


def test_concurrent_create_request_id_different_actor(app_client, monkeypatch):
    first_actor = _new_user("idempotency-first@example.test")
    second_actor = _new_user("idempotency-second@example.test")
    first_client, first_headers = _login_client(first_actor)
    hierarchy = _workspace_with_headers(first_client, first_headers)
    second_client, second_headers = _login_client(second_actor)
    request_id = uuid.uuid4()
    payload = _create_payload(hierarchy, request_id)
    from app.repositories.intervention_repository import SqlAlchemyInterventionRepository
    original_get = SqlAlchemyInterventionRepository.get_by_request_id
    fetches = []

    def observed_get(repository, value):
        result = original_get(repository, value)
        if value == request_id:
            fetches.append((threading.get_ident(), result is not None))
        return result

    monkeypatch.setattr(SqlAlchemyInterventionRepository, "get_by_request_id", observed_get)

    def create(client, headers):
        return client.post("/api/v1/interventions", headers=headers, json=payload)

    try:
        with _flush_race(mode="create", target_id=request_id) as (race, all_arrived):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(create, first_client, first_headers), executor.submit(create, second_client, second_headers)]
                assert all_arrived.wait(timeout=8)
                responses = [future.result(timeout=15) for future in futures]
    finally:
        first_client.close()
        second_client.close()

    assert len(race["arrivals"]) == 2
    assert len({session_id for session_id, _thread_id in race["arrivals"]}) == 2
    assert len({thread_id for _session_id, thread_id in race["arrivals"]}) == 2
    assert race["constraint_names"] == ["uq_interventions_client_request_id"]
    assert len(set(race["rollbacks"])) == 1
    assert sum(not found for _thread_id, found in fetches) == 2
    assert sum(found for _thread_id, found in fetches) == 1
    assert sorted(response.status_code for response in responses) == [201, 409]
    winner_index = next(index for index, response in enumerate(responses) if response.status_code == 201)
    winner = (first_actor, second_actor)[winner_index]
    item_id = responses[winner_index].json()["id"]
    from app.db import SessionLocal
    from app.models import AuditEvent, Intervention, InterventionEvent
    with SessionLocal() as session:
        rows = tuple(session.scalars(sa.select(Intervention).where(Intervention.client_request_id == request_id)))
        assert len(rows) == 1
        assert rows[0].created_by_user_id == winner.id
        assert session.scalar(sa.select(sa.func.count()).select_from(InterventionEvent).where(InterventionEvent.intervention_id == rows[0].id, InterventionEvent.event_type == "intervention_created")) == 1
        assert session.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(AuditEvent.entity_id == rows[0].id, AuditEvent.action == "intervention.created")) == 1
    events = _events(item_id, "intervention.created")
    assert len(events) == 1
    assert events[0].actor_user_id == winner.id
    assert events[0].actor_email_snapshot == winner.email
    assert events[0].request_id == uuid.UUID(responses[winner_index].headers["X-Request-ID"])
    assert events[0].request_id != uuid.UUID(responses[1 - winner_index].headers["X-Request-ID"])


def _workspace_with_headers(client, headers):
    project = client.post("/api/v1/projects", headers=headers, json={"name": "Race", "project_type": "Maintenance"}).json()
    environment = client.post(f"/api/v1/projects/{project['id']}/environments", headers=headers, json={"name": "Race env", "environment_type": "Workshop"}).json()
    obj = client.post(f"/api/v1/environments/{environment['id']}/objects", headers=headers, json={"category": "Machine", "name": "Race object"}).json()
    return project, environment, obj


def test_keyset_equal_timestamps_concurrent_insert_and_cursor_contract(intervention_client):
    client, actor = intervention_client
    hierarchy = _workspace(client)
    created = [client.post("/api/v1/interventions", json=_create_payload(hierarchy, title=f"Equal {index}")).json() for index in range(5)]
    fixed = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)

    from app.db import SessionLocal
    from app.models import Intervention

    with SessionLocal() as session:
        session.execute(sa.update(Intervention).where(Intervention.id.in_([uuid.UUID(item["id"]) for item in created])).values(created_at=fixed))
        session.commit()

    first = client.get("/api/v1/interventions", params={"limit": 2, "priority": "high"}).json()
    assert [item["id"] for item in first["items"]] == sorted((item["id"] for item in created), reverse=True)[:2]
    insert_gate = threading.Event()

    def concurrent_insert():
        insert_gate.wait(timeout=5)
        with SessionLocal() as session:
            antecedent = Intervention(
                client_request_id=uuid.uuid4(), client_request_fingerprint="a" * 64,
                project_id=uuid.UUID(hierarchy[0]["id"]), environment_id=uuid.UUID(hierarchy[1]["id"]),
                mra_object_id=uuid.UUID(hierarchy[2]["id"]), title="Inserted before cursor", priority="high",
                created_by_user_id=actor.id, created_at=fixed + timedelta(seconds=1),
            )
            session.add(antecedent)
            session.commit()
            return str(antecedent.id)

    with ThreadPoolExecutor(max_workers=1) as executor:
        inserted = executor.submit(concurrent_insert)
        insert_gate.set()
        antecedent_id = inserted.result(timeout=10)

    seen = [item["id"] for item in first["items"]]
    cursor = first["next_cursor"]
    while cursor:
        page = client.get("/api/v1/interventions", params={"limit": 2, "priority": "high", "cursor": cursor}).json()
        seen.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
    assert len(seen) == len(set(seen)) == 5
    assert set(seen) == {item["id"] for item in created}
    assert antecedent_id not in seen  # Newer rows before the cursor require a refreshed traversal.
    refreshed = client.get("/api/v1/interventions", params={"limit": 2, "priority": "high"}).json()
    assert refreshed["items"][0]["id"] == antecedent_id
    assert client.get("/api/v1/interventions", params={"limit": 3, "priority": "high", "cursor": first["next_cursor"]}).status_code == 200
    assert client.get("/api/v1/interventions", params={"limit": 2, "priority": "low", "cursor": first["next_cursor"]}).status_code == 422
    assert client.get("/api/v1/interventions", params={"limit": 2, "priority": "high", "cursor": "malformed"}).status_code == 422


def test_recently_completed_boundaries_are_inclusive_and_read_only(intervention_client, monkeypatch):
    client, actor = intervention_client
    hierarchy = _workspace(client)
    fixed = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)

    from app.db import SessionLocal
    from app.models import AuditEvent, Intervention
    from app.repositories import intervention_repository

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr(intervention_repository, "datetime", FixedDateTime)
    cases = [
        ("now", "completed", fixed),
        ("inside", "completed", fixed - timedelta(days=29, hours=23, minutes=59, seconds=59)),
        ("boundary", "completed", fixed - timedelta(days=30)),
        ("outside", "completed", fixed - timedelta(days=30, microseconds=1)),
        ("null", "completed", None),
        ("wrong-status", "open", fixed),
        ("cancelled", "cancelled", fixed),
        ("offset", "completed", (fixed - timedelta(days=1)).astimezone(timezone(timedelta(hours=2)))),
    ]
    with SessionLocal() as session:
        for index, (name, status, completed_at) in enumerate(cases):
            session.add(Intervention(
                client_request_id=uuid.uuid4(), client_request_fingerprint=f"{index + 1:064x}",
                project_id=uuid.UUID(hierarchy[0]["id"]), environment_id=uuid.UUID(hierarchy[1]["id"]),
                mra_object_id=uuid.UUID(hierarchy[2]["id"]), title=name, status=status,
                completed_at=completed_at, cancelled_at=fixed if status == "cancelled" else None,
                created_by_user_id=actor.id,
            ))
        session.commit()
        before = session.scalar(sa.select(sa.func.count()).select_from(AuditEvent))
    assert client.get("/api/v1/interventions/summary").json()["recently_completed"] == 4
    with SessionLocal() as session:
        assert session.scalar(sa.select(sa.func.count()).select_from(AuditEvent)) == before


def test_exact_eight_action_audit_contract_and_negative_assertions(intervention_client):
    client, actor = intervention_client
    hierarchy = _workspace(client)

    created_response = client.post("/api/v1/interventions", json=_create_payload(hierarchy))
    item = created_response.json()
    item_id = item["id"]
    expected_created = {
        "priority": {"before": None, "after": "high"},
        "status": {"before": None, "after": "open"},
        "title": {"before": None, "after": "Controllo pressa"},
        "version": {"before": None, "after": 1},
        "description": {"before_length": 0, "after_length": len("Verifica programmata")},
    }
    contracts = [("intervention.created", created_response, ["priority", "status", "title", "version", "description"], expected_created, {})]

    update_response = client.patch(f"/api/v1/interventions/{item_id}", json={"expected_version": item["version"], "title": "Pressa aggiornata", "description": "Testo nuovo e controllato"})
    item = update_response.json()
    update_changes = {
        "title": {"before": "Controllo pressa", "after": "Pressa aggiornata"},
        "version": {"before": 1, "after": 2},
        "description": {"before_length": len("Verifica programmata"), "after_length": len("Testo nuovo e controllato")},
    }
    contracts.append(("intervention.updated", update_response, ["title", "version", "description"], update_changes, {}))

    assign_response = client.patch(f"/api/v1/interventions/{item_id}", json={"expected_version": item["version"], "assigned_user_id": str(actor.id)})
    item = assign_response.json()
    contracts.append(("intervention.assigned", assign_response, ["assigned_user_id", "version"], {"assigned_user_id": {"before": None, "after": str(actor.id)}, "version": {"before": 2, "after": 3}}, {}))

    status_response = client.post(f"/api/v1/interventions/{item_id}/transitions", json={"command_id": str(uuid.uuid4()), "expected_version": item["version"], "to_status": "in_progress", "note": "Safe note"})
    item = client.get(f"/api/v1/interventions/{item_id}").json()
    status_result = status_response.json()
    status_changes = {
        "started_at": {"before": None, "after": datetime.fromisoformat(status_result["started_at"]).isoformat()},
        "status": {"before": "open", "after": "in_progress"},
        "version": {"before": 3, "after": 4},
    }
    contracts.append(("intervention.status.changed", status_response, ["started_at", "status", "version"], status_changes, {}))

    reopen_seed_response = client.post("/api/v1/interventions", json=_create_payload(hierarchy, assigned_user_id=str(actor.id), title="Da riaprire"))
    reopen_seed = reopen_seed_response.json()
    from app.db import SessionLocal
    from app.models import Intervention
    completed_at = datetime(2026, 8, 8, 10, tzinfo=timezone.utc)
    with SessionLocal() as session:
        session.execute(
            sa.update(Intervention).where(Intervention.id == uuid.UUID(reopen_seed["id"])).values(
                status="completed", completed_at=completed_at, resolution_summary="Risoluzione verificata", version=2,
            )
        )
        session.commit()
    reopen_before = client.get(f"/api/v1/interventions/{reopen_seed['id']}").json()
    reopened_response = client.post(f"/api/v1/interventions/{reopen_seed['id']}/transitions", json={"command_id": str(uuid.uuid4()), "expected_version": reopen_before["version"], "to_status": "in_progress", "note": "Riapertura sicura"})
    reopened_changes = {
        "completed_at": {"before": datetime.fromisoformat(reopen_before["completed_at"]).isoformat(), "after": None},
        "status": {"before": "completed", "after": "in_progress"},
        "version": {"before": 2, "after": 3},
        "resolution_summary": {"before_length": len("Risoluzione verificata"), "after_length": 0},
    }
    contracts.append(("intervention.reopened", reopened_response, ["completed_at", "status", "version", "resolution_summary"], reopened_changes, {}))

    cancelled_item_response = client.post("/api/v1/interventions", json=_create_payload(hierarchy, assigned_user_id=str(actor.id), title="Da annullare"))
    cancelled_item = cancelled_item_response.json()
    cancelled_response = client.post(f"/api/v1/interventions/{cancelled_item['id']}/transitions", json={"command_id": str(uuid.uuid4()), "expected_version": cancelled_item["version"], "to_status": "cancelled", "note": "Annullamento sicuro"})
    cancelled_result = cancelled_response.json()
    cancelled_changes = {
        "cancelled_at": {"before": None, "after": datetime.fromisoformat(cancelled_result["cancelled_at"]).isoformat()},
        "status": {"before": "open", "after": "cancelled"},
        "version": {"before": 1, "after": 2},
    }
    contracts.append(("intervention.cancelled", cancelled_response, ["cancelled_at", "status", "version"], cancelled_changes, {}))

    card = client.post("/api/v1/knowledge-cards", json={"code": "B0052-AUDIT", "title": "Audit", "category": "Test"}).json()
    link_response = client.post(f"/api/v1/interventions/{item_id}/knowledge", json={"knowledge_card_id": card["id"], "usage_type": "diagnostic_reference", "note": "Not audited"})
    link = link_response.json()
    metadata = {"usage_type": "diagnostic_reference", "knowledge_card_id": card["id"], "link_id": link["id"]}
    contracts.append(("intervention.knowledge.linked", link_response, [], {}, metadata))
    unlink_response = client.delete(f"/api/v1/interventions/{item_id}/knowledge/{link['id']}")
    contracts.append(("intervention.knowledge.unlinked", unlink_response, [], {}, metadata))

    actual_by_action = {}
    for action, response, changed_fields, changes, expected_metadata in contracts:
        entity_id = cancelled_item["id"] if action == "intervention.cancelled" else reopen_seed["id"] if action == "intervention.reopened" else item_id
        events = _events(entity_id, action)
        _assert_event(
            events,
            expected_action=action,
            expected_entity_type="intervention",
            expected_entity_id=entity_id,
            expected_actor_id=actor.id,
            expected_actor_email=actor.email,
            expected_request_id=response.headers["X-Request-ID"],
            expected_outcome="success",
            expected_changed_fields=changed_fields,
            expected_changes=changes,
            expected_metadata=expected_metadata,
            expected_event_count=1,
        )
        actual_by_action[action] = (events, response, entity_id, changed_fields, changes, expected_metadata)

    serialized_audit = [
        {
            "changed_fields": event.changed_fields,
            "changes": event.changes,
            "metadata": event.metadata_json,
        }
        for events, _response, _entity_id, _fields, _changes, _metadata in actual_by_action.values()
        for event in events
    ]
    serialized_text = str(serialized_audit)
    for forbidden in ("note", "fingerprint", "command_id", "client_request_id", "Risoluzione verificata", "Verifica programmata", "Testo nuovo e controllato"):
        assert forbidden not in serialized_text

    update_actual = actual_by_action["intervention.updated"]
    base = dict(
        events=update_actual[0], expected_action="intervention.updated", expected_entity_type="intervention",
        expected_entity_id=item_id, expected_actor_id=actor.id, expected_actor_email=actor.email,
        expected_request_id=update_actual[1].headers["X-Request-ID"], expected_outcome="success",
        expected_changed_fields=update_actual[3], expected_changes=update_actual[4], expected_metadata={}, expected_event_count=1,
    )
    mutations = [
        {"expected_actor_id": uuid.uuid4()}, {"expected_actor_email": "wrong@example.test"},
        {"expected_request_id": uuid.uuid4()}, {"expected_event_count": 2},
        {"expected_changed_fields": update_actual[3] + ["extra"]}, {"expected_changed_fields": update_actual[3][:-1]},
    ]
    for mutation in mutations:
        with pytest.raises(AssertionError):
            _assert_event(**{**base, **mutation})
    wrong_changes = []
    for field, member, value in (("title", "before", "wrong"), ("title", "after", "wrong"), ("description", "after_length", 999)):
        changed = copy.deepcopy(update_actual[4]); changed[field][member] = value; wrong_changes.append(changed)
    changed = copy.deepcopy(update_actual[4]); changed["extra"] = {"before": None, "after": "x"}; wrong_changes.append(changed)
    changed = copy.deepcopy(update_actual[4]); changed.pop("title"); wrong_changes.append(changed)
    for changed in wrong_changes:
        with pytest.raises(AssertionError):
            _assert_event(**{**base, "expected_changes": changed})
    linked = actual_by_action["intervention.knowledge.linked"]
    linked_base = dict(base, events=linked[0], expected_action="intervention.knowledge.linked", expected_request_id=linked[1].headers["X-Request-ID"], expected_changed_fields=[], expected_changes={}, expected_metadata=linked[5])
    for metadata in ({**linked[5], "extra": "x"}, {key: value for key, value in linked[5].items() if key != "link_id"}):
        with pytest.raises(AssertionError):
            _assert_event(**{**linked_base, "expected_metadata": metadata})
