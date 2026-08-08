from datetime import datetime, timezone
import uuid

import pytest

from app.services.audit_service import AUDIT_ACTIONS
from app.services.intervention_service import InterventionValidationError, _decode_cursor, canonical_fingerprint
from app.services.intervention_state_machine import InvalidTransitionError, TRANSITIONS, apply_transition
from app.services.intervention_note_policy import secure_operational_note
from app.repositories.intervention_repository import SqlAlchemyInterventionRepository
from app.audit_sanitizer import build_audit_diff
from app.schemas import InterventionKnowledgeCreate, InterventionTransition


def transition(current, target, **overrides):
    values = dict(current=current, target=target, role="admin", has_active_assignee=True, note="Motivo", resolution_summary="Risolto", started_at=None, current_resolution=None, now=datetime(2026, 8, 8, tzinfo=timezone.utc))
    values.update(overrides); return apply_transition(**values)


@pytest.mark.parametrize("current,target", [(source,target) for source,targets in TRANSITIONS.items() for target in targets])
def test_every_declared_transition_is_supported(current, target):
    result = transition(current, target)
    assert result.event_type == ("reopened" if current == "completed" else "status_changed")


@pytest.mark.parametrize("current,target", [(source,target) for source in TRANSITIONS for target in TRANSITIONS if target not in TRANSITIONS[source]])
def test_all_undeclared_and_same_state_transitions_are_rejected(current, target):
    with pytest.raises(InvalidTransitionError): transition(current, target)


def test_transition_business_requirements_and_timestamps():
    with pytest.raises(InvalidTransitionError): transition("open", "planned", has_active_assignee=False)
    with pytest.raises(InvalidTransitionError): transition("planned", "blocked", note=None)
    with pytest.raises(InvalidTransitionError): transition("in_progress", "completed", resolution_summary=" ")
    with pytest.raises(InvalidTransitionError): transition("open", "cancelled", role="editor")
    completed = transition("in_progress", "completed")
    assert completed.completed_at == datetime(2026, 8, 8, tzinfo=timezone.utc)
    reopened = transition("completed", "in_progress", current_resolution="La soluzione precedente")
    assert reopened.resolution_summary is None
    assert reopened.resolution_summary_snapshot == "La soluzione precedente"


def test_fingerprint_is_canonical_actor_bound_and_sensitive_to_payload():
    actor = uuid.uuid4()
    first = canonical_fingerprint({"title":"A", "priority":"normal"}, actor)
    assert first == canonical_fingerprint({"priority":"normal", "title":"A"}, actor)
    assert first != canonical_fingerprint({"title":"B", "priority":"normal"}, actor)
    assert first != canonical_fingerprint({"title":"A", "priority":"normal"}, uuid.uuid4())
    assert len(first) == 64


def test_invalid_cursor_is_rejected():
    with pytest.raises(InterventionValidationError): _decode_cursor("not-a-cursor")


def test_intervention_audit_catalog_is_complete():
    expected = {"intervention.created", "intervention.updated", "intervention.assigned", "intervention.status.changed", "intervention.reopened", "intervention.cancelled", "intervention.knowledge.linked", "intervention.knowledge.unlinked"}
    assert expected <= AUDIT_ACTIONS


@pytest.mark.parametrize("note", ["password=secret-value", "token: abcdefgh", "Bearer abcdefghijklmnop", "eyJabcde.abcdefgh.abcdefgh", "https://user:pass@example.test/path", "postgresql://user:pass@db/test", "API key = topsecret"])
def test_operational_note_rejects_credential_patterns(note):
    with pytest.raises(ValueError, match="Nota operativa non valida"):
        secure_operational_note(note)


def test_operational_note_normalizes_unicode_and_controls():
    assert secure_operational_note("  Ｎｏｔａ\x00 valida  ") == "Nota valida"


def test_intervention_repository_has_no_timeline_or_intervention_delete_mutator():
    forbidden = {"delete", "delete_event", "update_event", "delete_intervention", "update_intervention_event"}
    assert forbidden.isdisjoint(vars(SqlAlchemyInterventionRepository))
    assert "delete_knowledge_link" in vars(SqlAlchemyInterventionRepository)


def test_intervention_audit_diff_is_exact_and_long_text_is_length_only():
    before={"title":"Before","description":"long before","status":"open","priority":"normal","assigned_user_id":None,"resolution_summary":None,"version":1}
    after={"title":"After","description":"a much longer description","status":"in_progress","priority":"normal","assigned_user_id":"00000000-0000-0000-0000-000000000001","resolution_summary":"resolved secret-free text","version":2}
    fields,changes=build_audit_diff("intervention",before,after)
    assert fields==["assigned_user_id","status","title","version","description","resolution_summary"]
    assert changes=={"assigned_user_id":{"before":None,"after":"00000000-0000-0000-0000-000000000001"},"status":{"before":"open","after":"in_progress"},"title":{"before":"Before","after":"After"},"version":{"before":1,"after":2},"description":{"before_length":11,"after_length":25},"resolution_summary":{"before_length":0,"after_length":25}}
    assert "long before" not in str(changes) and "resolved secret-free text" not in str(changes)


def test_sensitive_notes_are_rejected_by_transition_and_knowledge_dtos():
    with pytest.raises(ValueError): InterventionTransition(command_id=uuid.uuid4(),expected_version=1,to_status="blocked",note="token=secret-value")
    with pytest.raises(ValueError): InterventionKnowledgeCreate(knowledge_card_id=uuid.uuid4(),usage_type="diagnostic_reference",note="Bearer abcdefghijklmnop")
