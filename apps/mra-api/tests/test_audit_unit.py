import json
import uuid
import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.audit_context import bind_audit_context, create_audit_context, current_audit_context, reset_audit_context
from app.audit_sanitizer import MAX_JSON_BYTES, SENSITIVE_KEYS, _sanitize, build_audit_diff, sanitize_json_field
from app.main import app
from app.db import get_db
from app.models import AuditEvent
from app.repositories.audit_repository import AuditRepositoryProtocol, SqlAlchemyAuditRepository
from app.services.audit_service import AUDIT_ACTIONS, AuditCursorError, AuditService, decode_cursor, encode_cursor
from app.services.auth_service import _is_user_email_conflict
from app.services.knowledge_relation_service import _is_relation_conflict


def test_sanitizer_removes_sensitive_nested_keys_controls_and_unsupported_types():
    value = {"safe": "hello\x00world", "nested": {"PASSWORD_HASH": "secret", "items": [{"token": "hidden", "ok": 1}]}, "object": object()}
    result = sanitize_json_field(value)
    rendered = json.dumps(result)
    assert "secret" not in rendered and "hidden" not in rendered and "\u0000" not in rendered
    assert result["safe"] == "helloworld"
    assert result["object"] == {"redacted": "unsupported_type"}


def test_sanitizer_limits_depth_items_strings_and_serialized_size():
    result = sanitize_json_field({"long": "x" * 1000, "items": list(range(100)), "deep": {"a": {"b": {"c": {"d": "hidden"}}}}})
    assert result["long"].startswith("x" * 256) and len(result["long"]) == 257
    assert len(result["items"]) == 51
    assert result["deep"]["a"]["b"]["c"]["d"] == {"truncated": "max_depth"}
    assert len(json.dumps(sanitize_json_field({"large": ["x" * 256] * 50})).encode()) <= 16 * 1024


def test_allowlisted_diff_uses_lengths_and_never_password_data():
    fields, changes = build_audit_diff("knowledge_card", {"title": "Old", "procedure": "a" * 20}, {"title": "New", "procedure": "b" * 40}, password_changed=True)
    assert fields == ["password"]
    assert changes == {}


def test_catalog_and_cursor_round_trip_and_malformed_cursor():
    assert {"auth.login.succeeded", "operation.failed", "project.deleted"} <= AUDIT_ACTIONS
    event = AuditEvent(id=uuid.uuid4(), occurred_at=datetime.now(UTC))
    assert decode_cursor(encode_cursor(event)) == (event.occurred_at, event.id, "")
    with pytest.raises(AuditCursorError): decode_cursor("not-a-cursor")


def test_request_context_and_response_ids_are_server_generated_and_isolated():
    contexts = [create_audit_context() for _ in range(20)]
    assert len({context.request_id for context in contexts}) == 20
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.get("/version", headers={"X-Request-ID": "00000000-0000-0000-0000-000000000000"}), range(12)))
    ids = [response.headers["X-Request-ID"] for response in responses]
    assert len(set(ids)) == 12
    assert "00000000-0000-0000-0000-000000000000" not in ids


@pytest.mark.parametrize("key", sorted(SENSITIVE_KEYS))
@pytest.mark.parametrize("container", ["root", "mapping", "list", "max_depth"])
def test_every_sensitive_key_is_removed_recursively_and_case_insensitively(key, container):
    sensitive = key.upper().replace("_", "-")
    value = {sensitive: "NEVER"} if container == "root" else ({"nested": {sensitive: "NEVER"}} if container == "mapping" else ({"nested": [{sensitive: "NEVER"}]} if container == "list" else {"a": {"b": {"c": {sensitive: "NEVER"}}}}))
    assert "NEVER" not in json.dumps(sanitize_json_field(value))


@pytest.mark.parametrize("variant", [
    "api_key", "api-key", "api.key", "api key", "api/key", "api\\key", "API KEY",
    "access_token", "access-token", "access.token", "access token", "access/token",
    "password", "pass.word", "pass word", "csrf.token", "database url",
    "authorization.header", "api::--//key", "ａｐｉ　ｋｅｙ",
])
@pytest.mark.parametrize("container", ["root", "mapping", "list"])
def test_sensitive_key_separator_and_unicode_variants_are_removed(variant, container):
    value = {variant: "EXFILTRATED"} if container == "root" else ({"safe": {variant: "EXFILTRATED"}} if container == "mapping" else {"safe": [{variant: "EXFILTRATED"}]})
    rendered = json.dumps(sanitize_json_field(value), ensure_ascii=False)
    assert "EXFILTRATED" not in rendered and variant not in rendered


def test_sanitizer_utf8_mapping_limits_uuid_datetime_and_no_repr():
    class Dangerous:
        def __repr__(self):
            raise AssertionError("repr must not be called")
    unsupported = sanitize_json_field({"uuid": uuid.uuid4(), "time": datetime.now(UTC), "danger": Dangerous()})
    assert all(value == {"redacted": "unsupported_type"} for value in unsupported.values())
    result = sanitize_json_field({f"k{i}": "value" for i in range(55)})
    assert len(result) == 51 and result["__truncated__"] == "max_items"
    assert len(json.dumps(result, ensure_ascii=False).encode()) <= 16 * 1024
    multibyte = sanitize_json_field({"large": ["€" * 256] * 50})
    assert multibyte == {"truncated": "size_limit"}


@pytest.mark.parametrize("ascii_tail,expected_size,truncated", [(66, MAX_JSON_BYTES - 1, False), (67, MAX_JSON_BYTES, False), (68, MAX_JSON_BYTES + 1, True)])
def test_json_utf8_byte_limit_below_at_and_above_boundary(ascii_tail, expected_size, truncated):
    payload = {f"k{i}": "€" * 256 for i in range(21)}
    payload["k21"] = "x" * ascii_tail
    raw = _sanitize(payload, 0)
    assert len(json.dumps(raw, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) == expected_size
    result = sanitize_json_field(payload)
    assert (result == {"truncated": "size_limit"}) is truncated


def test_nested_payload_can_cross_byte_limit_only_after_serialization():
    payload = {"outer": [{"value": "€" * 256} for _ in range(22)]}
    sanitized = _sanitize(payload, 0)
    assert len(json.dumps(sanitized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > MAX_JSON_BYTES
    assert sanitize_json_field(payload) == {"truncated": "size_limit"}


@pytest.mark.parametrize("entity_type", ["user", "knowledge_card", "knowledge_relation", "knowledge_revision", "project", "environment", "mra_object", "auth_session", "security"])
@pytest.mark.parametrize("mode", ["create", "update", "delete"])
def test_diff_supported_entity_types_create_update_delete(entity_type, mode):
    before = None if mode == "create" else {"status": "old", "description": "before"}
    after = None if mode == "delete" else {"status": "new", "description": "after"}
    fields, changes = build_audit_diff(entity_type, before, after)
    assert isinstance(fields, list) and isinstance(changes, dict)
    assert all(key in fields for key in changes)


def test_long_text_diff_records_only_lengths_and_unchanged_fields_are_absent():
    fields, changes = build_audit_diff("knowledge_card", {"title": "Same", "procedure": "a" * 10}, {"title": "Same", "procedure": "b" * 30})
    assert fields == ["procedure"]
    assert changes == {"procedure": {"before_length": 10, "after_length": 30}}


def test_cursor_is_bound_to_filters():
    class Repo:
        def list(self, **kwargs): return ()
    context = create_audit_context(); service = AuditService(Repo(), context)
    event = AuditEvent(id=uuid.uuid4(), occurred_at=datetime.now(UTC))
    from app.services.audit_service import _filter_signature
    cursor = encode_cursor(event, _filter_signature({"action": "project.created"}))
    with pytest.raises(AuditCursorError): service.list(cursor=cursor, action="project.deleted")


def test_contextvar_reset_and_frontend_catalog_matches_backend():
    context = create_audit_context(); token = bind_audit_context(context)
    assert current_audit_context() is context
    reset_audit_context(token)
    assert current_audit_context() is None
    apps_root = Path(__file__).parents[2]
    frontend = (apps_root / "mra-studio" / "src" / "pages" / "ActivityPage.tsx").read_text(encoding="utf-8")
    label_block = frontend.split("export const auditActionLabels", 1)[1].split("};", 1)[0]
    frontend_actions = set(re.findall(r'"([a-z_]+\.[a-z_.]+)"\s*:', label_block))
    assert frontend_actions == set(AUDIT_ACTIONS)
    assert "Evento non riconosciuto" in frontend
    catalog_source = (apps_root / "mra-api" / "app" / "services" / "audit_service.py").read_text(encoding="utf-8")
    constants = dict(re.findall(r'^([A-Z_]+)\s*=\s*"([a-z_]+\.[a-z_.]+)"', catalog_source, re.MULTILINE))
    emitted_source = "\n".join(path.read_text(encoding="utf-8") for path in (apps_root / "mra-api" / "app" / "services").glob("*.py") if path.name != "audit_service.py")
    assert set(constants.values()) == set(AUDIT_ACTIONS)
    assert all(name == "OPERATION_FAILED" or name in emitted_source for name in constants)


@pytest.mark.parametrize("constraint,user_conflict,relation_conflict", [
    ("ix_users_email", True, False),
    ("uq_knowledge_relation", False, True),
    ("ck_audit_events_outcome", False, False),
    (None, False, False),
])
def test_integrity_errors_are_classified_only_by_exact_constraint(constraint, user_conflict, relation_conflict):
    class Diag: constraint_name = constraint
    class Orig: diag = Diag()
    error = IntegrityError("statement", {}, Orig())
    assert _is_user_email_conflict(error) is user_conflict
    assert _is_relation_conflict(error) is relation_conflict


def test_request_id_is_returned_for_4xx_and_context_is_reset():
    with TestClient(app) as client:
        response = client.get("/does-not-exist", headers={"X-Request-ID": str(uuid.uuid4())})
    assert response.status_code == 404 and uuid.UUID(response.headers["X-Request-ID"])
    assert current_audit_context() is None


def test_request_id_is_returned_for_unhandled_5xx_and_error_is_generic():
    def broken_db():
        raise RuntimeError("database_url password traceback")
    app.dependency_overrides[get_db] = broken_db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 500 and uuid.UUID(response.headers["X-Request-ID"])
    assert response.json() == {"detail": "Errore interno del servizio."}


def test_contextvars_are_isolated_across_async_tasks():
    async def worker():
        context = create_audit_context(); token = bind_audit_context(context)
        try:
            await asyncio.sleep(0)
            return current_audit_context().request_id
        finally:
            reset_audit_context(token)
    async def run(): return await asyncio.gather(*(worker() for _ in range(20)))
    ids = asyncio.run(run())
    assert len(set(ids)) == 20 and current_audit_context() is None


def test_append_only_has_no_orm_cascade_or_repository_mutators():
    assert "entity_id" not in {fk.parent.name for fk in AuditEvent.__table__.foreign_keys}
    assert not AuditEvent.__mapper__.relationships
    assert not hasattr(AuditRepositoryProtocol, "update") and not hasattr(AuditRepositoryProtocol, "delete")
    assert not hasattr(SqlAlchemyAuditRepository, "update") and not hasattr(SqlAlchemyAuditRepository, "delete")
