from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.db import get_db
from app.main import app

client = TestClient(app)


class HealthyDatabase:
    def execute(self, statement):
        return None


class UnavailableDatabase:
    def execute(self, statement):
        raise SQLAlchemyError("database unavailable")


def override_database(database):
    def dependency():
        yield database

    return dependency


def test_health() -> None:
    app.dependency_overrides[get_db] = override_database(HealthyDatabase())
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["api"] == "ok"
    assert response.json()["database"] == "reachable"


def test_health_reports_database_failure() -> None:
    app.dependency_overrides[get_db] = override_database(UnavailableDatabase())
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Service unhealthy: database unavailable."
    }


def test_version() -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {
        "name": "MRA API",
        "version": "0.6.0",
        "environment": settings.app_env,
    }
