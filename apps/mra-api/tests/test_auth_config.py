import pytest
from pydantic import ValidationError

from app.config import Settings
from app.config import settings as runtime_settings
from app.routers.auth import _clear_auth_cookies, _set_auth_cookies
from fastapi import Response


def test_production_cookie_and_origin_configuration_is_enforced():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", session_cookie_secure=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", session_cookie_secure=True, session_cookie_name="mra_session", cors_origins="https://studio.example.test", auth_allowed_origins="https://studio.example.test")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", session_cookie_secure=True, session_cookie_name="__Host-mra_session", cors_origins="http://studio.example.test", auth_allowed_origins="http://studio.example.test")
    settings = Settings(_env_file=None, app_env="production", session_cookie_secure=True, session_cookie_name="__Host-mra_session", cors_origins="https://studio.example.test", auth_allowed_origins="https://studio.example.test")
    assert settings.csrf_cookie_name == "__Host-mra_csrf"


def test_development_uses_http_compatible_distinct_cookie_names():
    settings = Settings(_env_file=None, app_env="test", session_cookie_name="mra_session", session_cookie_secure=False)
    assert settings.session_cookie_name == "mra_session"
    assert settings.csrf_cookie_name == "mra_csrf"


def test_cors_and_auth_origin_allowlists_must_match():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins="http://localhost:5173", auth_allowed_origins="http://127.0.0.1:5173")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins="http://localhost:5173/", auth_allowed_origins="http://localhost:5173/")


@pytest.mark.parametrize(
    "origin",
    [
        "https://studio.example.test:bad",
        "https://studio.example.test:99999",
        "https://studio.example.test:0",
        "https://studio.example.test:",
        "https://studio.example.test:-1",
        "https://studio.example.test:443:444",
        "https://studio.example.test/path",
        "https://studio.example.test?query=1",
        "https://studio.example.test#fragment",
        "https://user:pass@studio.example.test",
        "https:///missing-host",
        "ftp://studio.example.test",
        " https://studio.example.test",
        "https://studio.example.test\n",
        "null",
    ],
)
def test_invalid_configured_origins_are_rejected(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=origin, auth_allowed_origins=origin)


@pytest.mark.parametrize(
    ("origin", "canonical"),
    [
        ("HTTP://LOCALHOST", "http://localhost"),
        ("http://localhost:80", "http://localhost"),
        ("HTTPS://STUDIO.EXAMPLE.TEST", "https://studio.example.test"),
        ("https://studio.example.test:443", "https://studio.example.test"),
        ("https://studio.example.test:8443", "https://studio.example.test:8443"),
        ("https://studio.example.test:65535", "https://studio.example.test:65535"),
    ],
)
def test_valid_configured_origins_are_canonicalized(origin, canonical):
    settings = Settings(_env_file=None, cors_origins=origin, auth_allowed_origins=origin)
    assert settings.cors_origin_list == [canonical]
    assert settings.auth_allowed_origin_list == [canonical]


def test_configured_origins_are_compared_canonically():
    settings = Settings(
        _env_file=None,
        app_env="production",
        session_cookie_secure=True,
        session_cookie_name="__Host-mra_session",
        cors_origins="HTTPS://STUDIO.EXAMPLE.TEST",
        auth_allowed_origins="https://studio.example.test:443",
    )
    assert settings.cors_origin_list == ["https://studio.example.test"]
    assert settings.auth_allowed_origin_list == ["https://studio.example.test"]


def test_production_set_and_delete_cookie_attributes(monkeypatch):
    monkeypatch.setattr(runtime_settings, "app_env", "production")
    monkeypatch.setattr(runtime_settings, "session_cookie_name", "__Host-mra_session")
    monkeypatch.setattr(runtime_settings, "session_cookie_secure", True)
    monkeypatch.setattr(runtime_settings, "session_cookie_samesite", "lax")
    response = Response()
    _set_auth_cookies(response, "session-token", "csrf-token")
    cookies = [value.decode() for key, value in response.raw_headers if key.lower() == b"set-cookie"]
    session = next(value for value in cookies if value.startswith("__Host-mra_session="))
    csrf = next(value for value in cookies if value.startswith("__Host-mra_csrf="))
    assert "Secure" in session and "HttpOnly" in session and "SameSite=lax" in session and "Path=/" in session and "Domain=" not in session
    assert "Secure" in csrf and "HttpOnly" not in csrf and "SameSite=lax" in csrf and "Path=/" in csrf and "Domain=" not in csrf
    cleared = Response(); _clear_auth_cookies(cleared)
    deleted = [value.decode() for key, value in cleared.raw_headers if key.lower() == b"set-cookie"]
    assert all("Max-Age=0" in value and "Secure" in value and "Path=/" in value for value in deleted)
