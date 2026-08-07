from fastapi.testclient import TestClient

from app.main import app


def test_cors_preflight_allows_only_configured_origin_headers_and_method():
    with TestClient(app) as client:
        allowed = client.options(
            "/api/v1/projects",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,X-CSRF-Token",
            },
        )
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "POST" in allowed.headers["access-control-allow-methods"]
        assert "x-csrf-token" in allowed.headers["access-control-allow-headers"].lower()

        denied = client.options(
            "/api/v1/projects",
            headers={"Origin": "https://evil.test", "Access-Control-Request-Method": "POST"},
        )
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers
