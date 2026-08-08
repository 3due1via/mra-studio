import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import threading

import pytest
import sqlalchemy as sa


@pytest.fixture
def intervention_client(app_client):
    from app.db import SessionLocal
    from app.dependencies import require_admin, require_csrf, require_editor, require_viewer
    from app.main import app
    from app.models import User

    actor = User(id=uuid.uuid4(), email="intervention-admin@example.test", display_name="Intervention Admin", password_hash="unused", role="admin", is_active=True)
    with SessionLocal() as session:
        session.add(actor); session.commit(); session.refresh(actor); session.expunge(actor)
    for dependency in (require_viewer, require_editor, require_admin): app.dependency_overrides[dependency] = lambda: actor
    app.dependency_overrides[require_csrf] = lambda: None
    yield app_client, actor
    for dependency in (require_viewer, require_editor, require_admin, require_csrf): app.dependency_overrides.pop(dependency, None)


def _workspace(client):
    project = client.post("/api/v1/projects", json={"name":"Build 005","project_type":"Maintenance","customer":"MRA","description":"","status":"active","progress":0}).json()
    environment = client.post(f"/api/v1/projects/{project['id']}/environments", json={"name":"Officina","environment_type":"Workshop"}).json()
    obj = client.post(f"/api/v1/environments/{environment['id']}/objects", json={"category":"Machine","name":"Pressa","status":"active"}).json()
    return project, environment, obj


def _create(client, project, environment, obj, request_id=None, **overrides):
    payload={"client_request_id":str(request_id or uuid.uuid4()),"project_id":project["id"],"environment_id":environment["id"],"mra_object_id":obj["id"],"title":"Controllo pressa","description":"Verifica programmata","priority":"high","assigned_user_id":None,"due_at":None};payload.update(overrides)
    return client.post("/api/v1/interventions",json=payload),payload


def test_intervention_end_to_end_idempotency_timeline_audit_and_restrict(intervention_client):
    client, actor = intervention_client; project, environment, obj = _workspace(client); request_id=uuid.uuid4()
    created,payload=_create(client,project,environment,obj,request_id); assert created.status_code==201; item=created.json(); assert item["code"].startswith("INT-")
    retry=client.post("/api/v1/interventions",json=payload); assert retry.status_code==201 and retry.json()["id"]==item["id"]
    conflict_payload={**payload,"title":"Payload differente"}; assert client.post("/api/v1/interventions",json=conflict_payload).status_code==409
    from app.db import SessionLocal
    from app.dependencies import require_editor
    from app.main import app
    from app.models import User
    with SessionLocal() as session:
        other_actor=User(email="other-create-actor@example.test",display_name="Other actor",password_hash="unused",role="admin",is_active=True);session.add(other_actor);session.commit();session.refresh(other_actor);session.expunge(other_actor)
    app.dependency_overrides[require_editor]=lambda:other_actor
    try: assert client.post("/api/v1/interventions",json=payload).status_code==409
    finally: app.dependency_overrides[require_editor]=lambda:actor
    assert client.get("/api/v1/interventions/summary").json()["open"]==1
    page=client.get("/api/v1/interventions",params={"search":item["code"]}).json(); assert [row["id"] for row in page["items"]]==[item["id"]]
    updated=client.patch(f"/api/v1/interventions/{item['id']}",json={"expected_version":item["version"],"title":"Controllo aggiornato"}); assert updated.status_code==200; item=updated.json()
    assert client.patch(f"/api/v1/interventions/{item['id']}",json={"expected_version":1,"priority":"urgent"}).status_code==409
    command_id=str(uuid.uuid4()); transition={"command_id":command_id,"expected_version":item["version"],"to_status":"in_progress","note":"Avvio"}
    assert client.post(f"/api/v1/interventions/{item['id']}/transitions",json=transition).status_code==409
    timeline=client.get(f"/api/v1/interventions/{item['id']}/timeline").json(); assert [event["event_type"] for event in timeline]==["intervention_created"]
    from app.db import engine
    with pytest.raises(sa.exc.DBAPIError), engine.begin() as connection:
        connection.execute(sa.text("UPDATE intervention_events SET event_type='status_changed' WHERE id=:id"), {"id":timeline[0]["id"]})
    with pytest.raises(sa.exc.DBAPIError), engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM intervention_events WHERE id=:id"), {"id":timeline[0]["id"]})
    assert client.delete(f"/api/v1/projects/{project['id']}").status_code==409
    from app.models import AuditEvent
    from sqlalchemy import select
    with SessionLocal() as session:
        events=session.scalars(select(AuditEvent).where(AuditEvent.entity_id==uuid.UUID(item["id"]))).all()
        assert [event.action for event in events]==["intervention.created","intervention.updated"]
        assert all(event.actor_user_id==actor.id for event in events)


def test_hierarchy_validation_no_delete_route_and_input_contract(intervention_client):
    client,_=intervention_client; p1,e1,o1=_workspace(client); p2,e2,o2=_workspace(client)
    response,_=_create(client,p1,e2,o2); assert response.status_code==422
    valid,_=_create(client,p1,e1,o1); assert valid.status_code==201
    assert client.delete(f"/api/v1/interventions/{valid.json()['id']}").status_code==405
    assert _create(client,p1,e1,o1,title=" ")[0].status_code==422
    assert _create(client,p1,e1,o1,priority="invalid")[0].status_code==422


def test_assignment_knowledge_complete_reopen_and_command_retry(intervention_client):
    client,actor=intervention_client; project,environment,obj=_workspace(client)
    created,_=_create(client,project,environment,obj); assert created.status_code==201; item=created.json()
    assigned=client.patch(f"/api/v1/interventions/{item['id']}",json={"expected_version":item["version"],"assigned_user_id":str(actor.id)});assert assigned.status_code==200;item=assigned.json()
    card=client.post("/api/v1/knowledge-cards",json={"code":"INT-KB-001","title":"Procedura pressa","category":"Maintenance","status":"published","version":"1.0.0"}).json()
    linked=client.post(f"/api/v1/interventions/{item['id']}/knowledge",json={"knowledge_card_id":card["id"],"usage_type":"procedure_applied","note":"Procedura verificata"}); assert linked.status_code==201
    assert client.delete(f"/api/v1/interventions/{item['id']}/knowledge/{linked.json()['id']}").status_code==204
    command=str(uuid.uuid4()); start={"command_id":command,"expected_version":item["version"],"to_status":"in_progress","note":"Avvio"}
    started=client.post(f"/api/v1/interventions/{item['id']}/transitions",json=start); assert started.status_code==200; started_result=started.json(); assert started_result["started_at"]
    retry=client.post(f"/api/v1/interventions/{item['id']}/transitions",json=start); assert retry.status_code==200 and retry.json()==started_result
    assert client.post(f"/api/v1/interventions/{item['id']}/transitions",json={**start,"note":"Different payload"}).status_code==409
    other=_create(client,project,environment,obj,assigned_user_id=str(actor.id))[0].json()
    assert client.post(f"/api/v1/interventions/{other['id']}/transitions",json=start).status_code==409
    from app.db import SessionLocal
    from app.dependencies import require_editor
    from app.main import app
    from app.models import User
    with SessionLocal() as session:
        second=User(email="second-command-actor@example.test",display_name="Second actor",password_hash="unused",role="admin",is_active=True);session.add(second);session.commit();session.refresh(second);session.expunge(second)
    app.dependency_overrides[require_editor]=lambda:second
    try: assert client.post(f"/api/v1/interventions/{item['id']}/transitions",json=start).status_code==409
    finally: app.dependency_overrides[require_editor]=lambda:actor
    item=client.get(f"/api/v1/interventions/{item['id']}").json()
    patched=client.patch(f"/api/v1/interventions/{item['id']}",json={"expected_version":item["version"],"title":"Changed after command"});assert patched.status_code==200
    assert client.post(f"/api/v1/interventions/{item['id']}/transitions",json=start).json()==started_result
    item=patched.json()
    completed=client.post(f"/api/v1/interventions/{item['id']}/transitions",json={"command_id":str(uuid.uuid4()),"expected_version":item["version"],"to_status":"completed","resolution_summary":"Sostituito componente"}); assert completed.status_code==200; item=client.get(f"/api/v1/interventions/{item['id']}").json()
    assert client.patch(f"/api/v1/interventions/{item['id']}",json={"expected_version":item["version"],"title":"Vietato"}).status_code==409
    assert client.post(f"/api/v1/interventions/{item['id']}/knowledge",json={"knowledge_card_id":card["id"],"usage_type":"solution_used","note":""}).status_code==409
    reopened=client.post(f"/api/v1/interventions/{item['id']}/transitions",json={"command_id":str(uuid.uuid4()),"expected_version":item["version"],"to_status":"in_progress","note":"Problema ricomparso"}); assert reopened.status_code==200; assert client.get(f"/api/v1/interventions/{item['id']}").json()["resolution_summary"] is None
    timeline=client.get(f"/api/v1/interventions/{item['id']}/timeline").json(); assert [event["event_type"] for event in timeline]==["intervention_created","assignment_changed","knowledge_linked","knowledge_unlinked","status_changed","status_changed","reopened"]
    assert timeline[-1]["resolution_summary_snapshot"]=="Sostituito componente"


def test_filters_search_overdue_and_keyset_are_discriminating(intervention_client):
    client,actor=intervention_client; p1,e1,o1=_workspace(client);p2,e2,o2=_workspace(client);now=datetime.now(timezone.utc)
    rows=[]
    for hierarchy,title,priority,due in [((p1,e1,o1),"Literal % value","urgent",now-timedelta(days=1)),((p1,e1,o1),"Literal _ value","low",None),((p2,e2,o2),"Back\\slash","normal",now+timedelta(days=1)),((p2,e2,o2),"Ordinary","high",now)]:
        response,_=_create(client,*hierarchy,title=title,priority=priority,assigned_user_id=str(actor.id),due_at=due.isoformat() if due else None);assert response.status_code==201;rows.append(response.json())
    assert len(client.get("/api/v1/interventions",params={"project_id":p1["id"]}).json()["items"])==2
    assert len(client.get("/api/v1/interventions",params={"environment_id":e2["id"]}).json()["items"])==2
    assert len(client.get("/api/v1/interventions",params={"mra_object_id":o1["id"]}).json()["items"])==2
    assert len(client.get("/api/v1/interventions",params={"assigned_user_id":str(actor.id)}).json()["items"])==4
    assert len(client.get("/api/v1/interventions",params={"priority":"urgent"}).json()["items"])==1
    assert len(client.get("/api/v1/interventions",params={"created_by_user_id":str(actor.id)}).json()["items"])==4
    assert len(client.get("/api/v1/interventions",params={"status":"open"}).json()["items"])==4
    assert len(client.get("/api/v1/interventions",params={"due_from":(now+timedelta(hours=12)).isoformat()}).json()["items"])==1
    assert len(client.get("/api/v1/interventions",params={"due_to":(now-timedelta(hours=12)).isoformat()}).json()["items"])==1
    assert client.get("/api/v1/interventions",params={"project_id":p1["id"],"priority":"high"}).json()["items"]==[]
    assert [x["title"] for x in client.get("/api/v1/interventions",params={"search":"%"}).json()["items"]]==["Literal % value"]
    assert [x["title"] for x in client.get("/api/v1/interventions",params={"search":"_"}).json()["items"]]==["Literal _ value"]
    assert [x["title"] for x in client.get("/api/v1/interventions",params={"search":"back\\slash"}).json()["items"]]==["Back\\slash"]
    assert client.get("/api/v1/interventions",params={"search":"Verifica programmata"}).json()["items"]==[]
    assert len(client.get("/api/v1/interventions",params={"overdue":"true"}).json()["items"])==1
    assert len(client.get("/api/v1/interventions",params={"overdue":"false"}).json()["items"])==3
    summary=client.get("/api/v1/interventions/summary").json();assert summary=={"open":4,"in_progress":0,"overdue":1,"recently_completed":0}
    first=client.get("/api/v1/interventions",params={"limit":1}).json();assert len(first["items"])==1 and first["next_cursor"]
    second=client.get("/api/v1/interventions",params={"limit":1,"cursor":first["next_cursor"]}).json();assert first["items"][0]["id"]!=second["items"][0]["id"]
    assert client.get("/api/v1/interventions",params={"limit":1,"cursor":first["next_cursor"],"priority":"urgent"}).status_code==422
    assert client.get("/api/v1/interventions",params={"limit":101}).status_code==422


def test_postgresql_sequence_concurrency_and_rollback_gap(intervention_client):
    _client,actor=intervention_client;project,environment,obj=_workspace(_client)
    from app.db import SessionLocal, engine
    from app.models import Intervention
    barrier=threading.Barrier(6)
    def insert(index:int):
        with SessionLocal() as session:
            value=Intervention(client_request_id=uuid.uuid4(),client_request_fingerprint=f"{index:064x}",project_id=uuid.UUID(project["id"]),environment_id=uuid.UUID(environment["id"]),mra_object_id=uuid.UUID(obj["id"]),title=f"Concurrent {index}",created_by_user_id=actor.id)
            session.add(value);barrier.wait(timeout=5);session.flush();code=value.code;session.commit();return code
    with ThreadPoolExecutor(max_workers=6) as executor:
        codes=list(executor.map(insert,range(6)))
    assert len(set(codes))==6 and all(code.startswith("INT-") and len(code)>=10 for code in codes)
    with SessionLocal() as session:
        rolled=Intervention(client_request_id=uuid.uuid4(),client_request_fingerprint="f"*64,project_id=uuid.UUID(project["id"]),environment_id=uuid.UUID(environment["id"]),mra_object_id=uuid.UUID(obj["id"]),title="Rolled back",created_by_user_id=actor.id);session.add(rolled);session.flush();rolled_number=int(rolled.code.split("-")[1]);session.rollback()
    with SessionLocal() as session:
        after=Intervention(client_request_id=uuid.uuid4(),client_request_fingerprint="e"*64,project_id=uuid.UUID(project["id"]),environment_id=uuid.UUID(environment["id"]),mra_object_id=uuid.UUID(obj["id"]),title="After rollback",created_by_user_id=actor.id);session.add(after);session.flush();after_number=int(after.code.split("-")[1]);session.commit()
    assert after_number>rolled_number
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT 'INT-' || lpad('1000000', 6, '0')"))=="INT-1000000"


def test_concurrent_patch_transition_and_idempotent_create(intervention_client):
    client,actor=intervention_client;project,environment,obj=_workspace(client);request_id=uuid.uuid4();barrier=threading.Barrier(2)
    payload={"client_request_id":str(request_id),"project_id":project["id"],"environment_id":environment["id"],"mra_object_id":obj["id"],"title":"Idempotent","description":"","priority":"normal","assigned_user_id":str(actor.id),"due_at":None}
    def create(): barrier.wait(timeout=5);return client.post("/api/v1/interventions",json=payload)
    with ThreadPoolExecutor(max_workers=2) as executor: responses=list(executor.map(lambda _x:create(),range(2)))
    assert [response.status_code for response in responses]==[201,201];assert len({response.json()["id"] for response in responses})==1;item=responses[0].json()
    barrier=threading.Barrier(2)
    def patch(index): barrier.wait(timeout=5);return client.patch(f"/api/v1/interventions/{item['id']}",json={"expected_version":item["version"],"title":f"Winner {index}"})
    with ThreadPoolExecutor(max_workers=2) as executor: patches=list(executor.map(patch,range(2)))
    assert sorted(response.status_code for response in patches)==[200,409]
    current=client.get(f"/api/v1/interventions/{item['id']}").json();assert current["version"]==item["version"]+1
    barrier=threading.Barrier(2)
    def transition(index): barrier.wait(timeout=5);return client.post(f"/api/v1/interventions/{item['id']}/transitions",json={"command_id":str(uuid.uuid4()),"expected_version":current["version"],"to_status":"in_progress","note":f"Worker {index}"})
    with ThreadPoolExecutor(max_workers=2) as executor: transitions=list(executor.map(transition,range(2)))
    assert sorted(response.status_code for response in transitions)==[200,409]
    from app.db import SessionLocal
    from app.models import AuditEvent,Intervention,InterventionEvent
    with SessionLocal() as session:
        iid=uuid.UUID(item["id"]);assert session.scalar(sa.select(sa.func.count()).select_from(Intervention).where(Intervention.client_request_id==request_id))==1
        assert session.scalar(sa.select(sa.func.count()).select_from(InterventionEvent).where(InterventionEvent.intervention_id==iid,InterventionEvent.event_type=="intervention_created"))==1
        assert session.scalar(sa.select(sa.func.count()).select_from(InterventionEvent).where(InterventionEvent.intervention_id==iid,InterventionEvent.event_type=="status_changed"))==1
        assert session.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(AuditEvent.entity_id==iid,AuditEvent.action=="intervention.created"))==1
        assert session.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(AuditEvent.entity_id==iid,AuditEvent.action=="intervention.updated"))==1
        assert session.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(AuditEvent.entity_id==iid,AuditEvent.action=="intervention.status.changed"))==1


@pytest.mark.parametrize("case", ["create", "patch", "transition", "link", "unlink"])
def test_real_audit_flush_failure_rolls_back_intervention_timeline_and_links(intervention_client, monkeypatch, case):
    client,actor=intervention_client;project,environment,obj=_workspace(client);item=None;card=None;link=None
    if case!="create": item=_create(client,project,environment,obj,assigned_user_id=str(actor.id))[0].json()
    if case in {"link","unlink"}:
        card=client.post("/api/v1/knowledge-cards",json={"code":f"AUDIT-{case}","title":"Audit card","category":"Test"}).json()
    if case=="unlink": link=client.post(f"/api/v1/interventions/{item['id']}/knowledge",json={"knowledge_card_id":card["id"],"usage_type":"diagnostic_reference","note":"Safe"}).json()
    from app.repositories.audit_repository import SqlAlchemyAuditRepository
    original_add=SqlAlchemyAuditRepository.add;failures=[]
    def fail_success(self,event):
        if event.action!="operation.failed":
            event.outcome="invalid-test-outcome"
            try:return original_add(self,event)
            except sa.exc.IntegrityError as exc:failures.append((exc.orig.diag.constraint_name,not self.db.is_active));raise
        return original_add(self,event)
    monkeypatch.setattr(SqlAlchemyAuditRepository,"add",fail_success)
    if case=="create": response,_=_create(client,project,environment,obj,title="Rolled back create")
    elif case=="patch": response=client.patch(f"/api/v1/interventions/{item['id']}",json={"expected_version":item["version"],"title":"Rolled back patch"})
    elif case=="transition": response=client.post(f"/api/v1/interventions/{item['id']}/transitions",json={"command_id":str(uuid.uuid4()),"expected_version":item["version"],"to_status":"in_progress","note":"Safe"})
    elif case=="link": response=client.post(f"/api/v1/interventions/{item['id']}/knowledge",json={"knowledge_card_id":card["id"],"usage_type":"diagnostic_reference","note":"Safe"})
    else: response=client.delete(f"/api/v1/interventions/{item['id']}/knowledge/{link['id']}")
    assert response.status_code==500 and failures==[("ck_audit_events_outcome",True)]
    from app.db import SessionLocal
    from app.models import AuditEvent,Intervention,InterventionEvent,InterventionKnowledgeLink
    with SessionLocal() as session:
        events=tuple(session.scalars(sa.select(AuditEvent).where(AuditEvent.action=="operation.failed")));assert len(events)==1 and events[0].metadata_json=={"code":"intervention_persistence_error"}
        if case=="create": assert session.scalar(sa.select(Intervention).where(Intervention.title=="Rolled back create")) is None
        elif case=="patch": assert session.get(Intervention,uuid.UUID(item["id"])).title==item["title"]
        elif case=="transition": assert session.get(Intervention,uuid.UUID(item["id"])).status=="open" and session.scalar(sa.select(sa.func.count()).select_from(InterventionEvent).where(InterventionEvent.intervention_id==uuid.UUID(item["id"]),InterventionEvent.event_type=="status_changed"))==0
        elif case=="link": assert session.scalar(sa.select(sa.func.count()).select_from(InterventionKnowledgeLink).where(InterventionKnowledgeLink.intervention_id==uuid.UUID(item["id"])))==0
        else: assert session.get(InterventionKnowledgeLink,uuid.UUID(link["id"])) is not None


def test_intervention_double_audit_failure_returns_generic_503(intervention_client, monkeypatch):
    client,_actor=intervention_client;project,environment,obj=_workspace(client)
    from app.repositories.audit_repository import SqlAlchemyAuditRepository
    original_add=SqlAlchemyAuditRepository.add;attempts=[]
    def fail(self,event):
        event.outcome="invalid-test-outcome"
        try:return original_add(self,event)
        except sa.exc.IntegrityError as exc:attempts.append((event.action,exc.orig.diag.constraint_name,not self.db.is_active));raise
    monkeypatch.setattr(SqlAlchemyAuditRepository,"add",fail)
    response,_=_create(client,project,environment,obj,title="Never committed")
    assert response.status_code==503 and response.json()=={"detail":"Servizio temporaneamente non disponibile."}
    assert len(attempts)==2 and [value[0] for value in attempts]==["intervention.created","operation.failed"]


def test_concurrent_identical_command_returns_same_persisted_result(intervention_client):
    client,actor=intervention_client;project,environment,obj=_workspace(client);item=_create(client,project,environment,obj,assigned_user_id=str(actor.id))[0].json();command=str(uuid.uuid4());barrier=threading.Barrier(2)
    payload={"command_id":command,"expected_version":item["version"],"to_status":"in_progress","note":"Concurrent retry"}
    def execute():barrier.wait(timeout=5);return client.post(f"/api/v1/interventions/{item['id']}/transitions",json=payload)
    with ThreadPoolExecutor(max_workers=2) as executor:responses=list(executor.map(lambda _x:execute(),range(2)))
    assert [response.status_code for response in responses]==[200,200] and responses[0].json()==responses[1].json()
    from app.db import SessionLocal
    from app.models import AuditEvent,InterventionEvent
    with SessionLocal() as session:
        iid=uuid.UUID(item["id"]);assert session.scalar(sa.select(sa.func.count()).select_from(InterventionEvent).where(InterventionEvent.intervention_id==iid,InterventionEvent.command_id==uuid.UUID(command)))==1
        assert session.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(AuditEvent.entity_id==iid,AuditEvent.action=="intervention.status.changed"))==1


def test_real_composite_constraints_and_all_restrict_policies(intervention_client):
    client,actor=intervention_client;p1,e1,o1=_workspace(client);p2,e2,o2=_workspace(client)
    from app.db import SessionLocal
    from app.models import Intervention
    violations=[]
    for project_id,environment_id,object_id in ((p1["id"],e2["id"],o2["id"]),(p2["id"],e2["id"],o1["id"])):
        with SessionLocal() as session:
            session.add(Intervention(client_request_id=uuid.uuid4(),client_request_fingerprint="d"*64,project_id=uuid.UUID(project_id),environment_id=uuid.UUID(environment_id),mra_object_id=uuid.UUID(object_id),title="Invalid hierarchy",created_by_user_id=actor.id))
            with pytest.raises(sa.exc.IntegrityError) as captured:session.flush()
            violations.append(captured.value.orig.diag.constraint_name);session.rollback()
    assert set(violations)=={"fk_interventions_environment_project","fk_interventions_object_environment"}
    intervention=_create(client,p1,e1,o1,assigned_user_id=str(actor.id))[0].json()
    assert client.delete(f"/api/v1/projects/{p1['id']}").status_code==409
    assert client.delete(f"/api/v1/environments/{e1['id']}").status_code==409
    assert client.delete(f"/api/v1/objects/{o1['id']}").status_code==409
    card=client.post("/api/v1/knowledge-cards",json={"code":"RESTRICT-CARD","title":"Restricted","category":"Test"}).json()
    link=client.post(f"/api/v1/interventions/{intervention['id']}/knowledge",json={"knowledge_card_id":card["id"],"usage_type":"diagnostic_reference","note":"Safe"}).json()
    assert client.delete(f"/api/v1/knowledge-cards/{card['id']}").status_code==409
    assert client.delete(f"/api/v1/interventions/{intervention['id']}/knowledge/{link['id']}").status_code==204
    assert client.delete(f"/api/v1/knowledge-cards/{card['id']}").status_code==204
