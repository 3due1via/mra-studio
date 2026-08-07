import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.browser_security import parse_origin, parse_referer_origin, validate_browser_request


def _request(**headers: str) -> Request:
    raw_headers = [(name.replace("_", "-").lower().encode(), value.encode()) for name, value in headers.items()]
    return Request({"type": "http", "method": "POST", "path": "/", "headers": raw_headers})


def test_origin_parser_accepts_case_and_normalizes_ports():
    assert parse_origin("HTTP://LOCALHOST:5173") == ("http", "localhost", 5173)
    assert parse_origin("http://example.test") == ("http", "example.test", 80)
    assert parse_origin("https://example.test") == ("https", "example.test", 443)
    assert parse_origin("https://example.test:8443") == ("https", "example.test", 8443)


@pytest.mark.parametrize(
    "value",
    [
        "http://localhost:5173/",
        "http://localhost:5173/path",
        "http://localhost:5173?query=1",
        "http://localhost:5173#fragment",
        "http://user:password@localhost:5173",
        "null",
        "ftp://localhost:5173",
        "http://localhost:invalid",
        "HTTP://LOCALHOST:5173/evil?x=1#fragment",
        " http://localhost:5173",
        "http://localhost:5173\n",
    ],
)
def test_origin_parser_rejects_non_origin_syntax(value):
    assert parse_origin(value) is None


def test_origin_policy_rejects_subdomain_prefix_and_suffix_attacks():
    for origin in (
        "http://localhost:5173.evil.test",
        "http://evil-localhost:5173",
        "http://localhost.evil:5173",
    ):
        with pytest.raises(HTTPException) as caught:
            validate_browser_request(_request(origin=origin))
        assert caught.value.status_code == 403


def test_referer_parser_accepts_path_query_and_rejects_malicious_values():
    assert parse_referer_origin("http://localhost:5173/login?next=%2Fprojects") == ("http", "localhost", 5173)
    assert parse_referer_origin("https://EXAMPLE.test/path") == ("https", "example.test", 443)
    assert parse_referer_origin("http://user:password@localhost:5173/path") is None
    assert parse_referer_origin("//localhost:5173/path") is None
    assert parse_referer_origin("javascript:alert(1)") is None
