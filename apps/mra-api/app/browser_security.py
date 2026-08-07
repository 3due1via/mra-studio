from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status

from app.config import CanonicalOrigin, parse_canonical_origin, settings

def _has_unsafe_raw_syntax(value: str) -> bool:
    return value != value.strip() or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)


def parse_origin(value: str) -> CanonicalOrigin | None:
    """Parse the strict Origin grammar: scheme://hostname[:port]."""
    return parse_canonical_origin(value)


def parse_referer_origin(value: str) -> CanonicalOrigin | None:
    """Extract an origin from an absolute Referer URL while allowing path/query."""
    if not value or value.lower() == "null" or _has_unsafe_raw_syntax(value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username or parsed.password or parsed.fragment:
            return None
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        return parsed.scheme.lower(), parsed.hostname.lower(), port
    except ValueError:
        return None


def normalized_allowlist() -> frozenset[CanonicalOrigin]:
    origins = {parse_origin(value) for value in settings.auth_allowed_origin_list}
    return frozenset(origin for origin in origins if origin is not None)


def validate_browser_request(request: Request) -> None:
    if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
        _reject()
    origin = request.headers.get("origin")
    if origin is not None:
        candidate = parse_origin(origin)
    else:
        referer = request.headers.get("referer")
        candidate = parse_referer_origin(referer) if referer is not None else None
    if candidate is None or candidate not in normalized_allowlist():
        _reject()


def _reject() -> None:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Richiesta non consentita.")
