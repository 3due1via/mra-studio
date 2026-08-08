import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

MAX_DEPTH = 4
MAX_ITEMS = 50
MAX_STRING_LENGTH = 256
MAX_JSON_BYTES = 16 * 1024

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "session_token",
        "csrf",
        "csrf_token",
        "cookie",
        "authorization",
        "secret",
        "api_key",
        "database_url",
        "sqlalchemy_url",
    }
)
SENSITIVE_COMPACT_KEYS = frozenset(key.replace("_", "") for key in SENSITIVE_KEYS)

CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def _normalized_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    pieces: list[str] = []
    separator = False
    for character in normalized:
        if character.isalnum():
            pieces.append(character)
            separator = False
        elif not separator:
            pieces.append("_")
            separator = True
    return "".join(pieces).strip("_")


def _is_sensitive_key(value: str) -> bool:
    normalized = _normalized_key(value)
    compact = normalized.replace("_", "")
    return normalized in SENSITIVE_KEYS or any(
        compact == sensitive or compact.startswith(sensitive)
        for sensitive in SENSITIVE_COMPACT_KEYS
    )


def _safe_string(value: str) -> str:
    cleaned = CONTROL_CHARACTERS.sub("", value)
    if len(cleaned) > MAX_STRING_LENGTH:
        return cleaned[:MAX_STRING_LENGTH] + "…"
    return cleaned


def _sanitize(value: Any, depth: int) -> Any:
    if depth > MAX_DEPTH:
        return {"truncated": "max_depth"}
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _safe_string(value)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_ITEMS:
                result["__truncated__"] = "max_items"
                break
            if not isinstance(key, str):
                continue
            safe_key = _safe_string(key)
            if _is_sensitive_key(safe_key):
                continue
            result[safe_key] = _sanitize(item, depth + 1)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        result = [_sanitize(item, depth + 1) for item in value[:MAX_ITEMS]]
        if len(value) > MAX_ITEMS:
            result.append({"truncated": "max_items"})
        return result
    return {"redacted": "unsupported_type"}


def sanitize_json_field(value: Any) -> Any:
    sanitized = _sanitize(value, 0)
    encoded = json.dumps(sanitized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_JSON_BYTES:
        return {"truncated": "size_limit"}
    return sanitized


SHORT_FIELDS: dict[str, frozenset[str]] = {
    "user": frozenset({"email", "display_name", "role", "is_active", "must_change_password"}),
    "knowledge_card": frozenset({"code", "title", "category", "status", "version"}),
    "knowledge_relation": frozenset({"source_id", "target_id", "relation_type"}),
    "knowledge_revision": frozenset({"card_id", "revision_number"}),
    "project": frozenset({"name", "project_type", "customer", "status", "progress"}),
    "environment": frozenset({"project_id", "name", "environment_type", "area_m2", "height_m", "width_m", "length_m"}),
    "mra_object": frozenset({"environment_id", "category", "name", "brand", "model", "serial_number", "status"}),
    "intervention": frozenset({"title", "status", "priority", "assigned_user_id", "due_at", "started_at", "completed_at", "cancelled_at", "version"}),
    "auth_session": frozenset(),
    "security": frozenset(),
}

LONG_FIELDS: dict[str, frozenset[str]] = {
    "knowledge_card": frozenset({"summary", "symptoms", "causes", "diagnosis", "procedure", "tools", "safety"}),
    "knowledge_relation": frozenset({"note"}),
    "project": frozenset({"description"}),
    "environment": frozenset({"notes"}),
    "mra_object": frozenset({"description", "metadata_json"}),
    "intervention": frozenset({"description", "resolution_summary"}),
}


def build_audit_diff(
    entity_type: str,
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any] | None,
    *,
    password_changed: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    if password_changed:
        return ["password"], {}
    before = before or {}
    after = after or {}
    changed_fields: list[str] = []
    changes: dict[str, Any] = {}
    for field in sorted(SHORT_FIELDS.get(entity_type, frozenset())):
        old = before.get(field)
        new = after.get(field)
        if old != new:
            changed_fields.append(field)
            changes[field] = {"before": old, "after": new}
    for field in sorted(LONG_FIELDS.get(entity_type, frozenset())):
        old = before.get(field)
        new = after.get(field)
        if old != new:
            changed_fields.append(field)
            changes[field] = {
                "before_length": len(old) if isinstance(old, (str, Mapping, Sequence)) else 0,
                "after_length": len(new) if isinstance(new, (str, Mapping, Sequence)) else 0,
            }
    return sanitize_json_field(changed_fields), sanitize_json_field(changes)
