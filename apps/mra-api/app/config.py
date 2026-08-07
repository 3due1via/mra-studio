from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlsplit

CanonicalOrigin = tuple[str, str, int]


def parse_canonical_origin(value: str) -> CanonicalOrigin | None:
    """Parse exactly scheme://hostname[:port] and normalize its origin."""
    if (
        not value
        or value.lower() == "null"
        or value != value.strip()
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.netloc.endswith(":")
        ):
            return None
        port = parsed.port
    except ValueError:
        return None
    if port is not None and not 1 <= port <= 65535:
        return None
    return (
        parsed.scheme.lower(),
        parsed.hostname.lower(),
        port or (443 if parsed.scheme.lower() == "https" else 80),
    )


def canonical_origin_text(origin: CanonicalOrigin) -> str:
    scheme, hostname, port = origin
    default_port = 443 if scheme == "https" else 80
    return f"{scheme}://{hostname}" if port == default_port else f"{scheme}://{hostname}:{port}"


def parse_origin_list(value: str) -> tuple[CanonicalOrigin, ...]:
    raw_origins = value.split(",")
    parsed_origins = tuple(parse_canonical_origin(origin) for origin in raw_origins)
    if not raw_origins or any(origin is None for origin in parsed_origins):
        raise ValueError("Origins must contain only scheme, host and optional valid port")
    return tuple(origin for origin in parsed_origins if origin is not None)


class Settings(BaseSettings):
    app_name: str = "MRA API"
    app_version: str = "0.6.0"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://mra:mra_dev_password@postgres:5432/mra"
    cors_origins: str = "http://localhost:5173"
    session_cookie_name: str = "mra_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_absolute_ttl_seconds: int = 43200
    session_idle_ttl_seconds: int = 1800
    auth_allowed_origins: str = "http://localhost:5173"
    auth_max_failed_attempts: int = 5
    auth_lock_seconds: int = 300
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [canonical_origin_text(origin) for origin in parse_origin_list(self.cors_origins)]

    @property
    def auth_allowed_origin_list(self) -> list[str]:
        return [canonical_origin_text(origin) for origin in parse_origin_list(self.auth_allowed_origins)]

    @model_validator(mode="after")
    def validate_production_auth(self):
        production = self.app_env.lower() == "production"
        canonical_cors = set(parse_origin_list(self.cors_origins))
        canonical_auth = set(parse_origin_list(self.auth_allowed_origins))
        if production:
            if not self.session_cookie_secure:
                raise ValueError("SESSION_COOKIE_SECURE must be true in production")
            if not self.session_cookie_name.startswith("__Host-"):
                raise ValueError("SESSION_COOKIE_NAME must use the __Host- prefix in production")
            if self.session_cookie_samesite.lower() != "lax":
                raise ValueError("SESSION_COOKIE_SAMESITE must be lax in production")
            if "*" in self.cors_origin_list or "*" in self.auth_allowed_origin_list:
                raise ValueError("Wildcard origins are forbidden in production")
            if any(origin[0] != "https" for origin in canonical_cors | canonical_auth if origin is not None):
                raise ValueError("Production origins must use HTTPS")
        if not self.cors_origin_list or not self.auth_allowed_origin_list:
            raise ValueError("CORS and authentication origin allowlists cannot be empty")
        if canonical_cors != canonical_auth:
            raise ValueError("CORS_ORIGINS and AUTH_ALLOWED_ORIGINS must contain the same origins")
        return self

    @property
    def csrf_cookie_name(self) -> str:
        return "__Host-mra_csrf" if self.app_env.lower() == "production" else "mra_csrf"


settings = Settings()
