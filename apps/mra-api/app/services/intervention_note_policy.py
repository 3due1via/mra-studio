import re
import unicodedata

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(?:password|passphrase|token|secret|api[\s_.-]*key|cookie|authorization|csrf)\b\s*[:=]"
)
BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{8,}")
JWT_TOKEN = re.compile(r"\beyJ[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{5,}\b")
URL_USERINFO = re.compile(r"(?i)\bhttps?://[^\s/@:]+:[^\s/@]+@")
DATABASE_URL = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|mongodb|redis)://")


def secure_operational_note(value: str | None, *, maximum: int = 1_000) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value)
    normalized = CONTROL_CHARACTERS.sub("", normalized).strip()
    if len(normalized) > maximum:
        raise ValueError("Nota operativa non valida.")
    if any(pattern.search(normalized) for pattern in (SENSITIVE_ASSIGNMENT, BEARER_TOKEN, JWT_TOKEN, URL_USERINFO, DATABASE_URL)):
        raise ValueError("Nota operativa non valida.")
    return normalized or None
