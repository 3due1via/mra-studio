import os

import pytest
from sqlalchemy.engine import make_url

test_database_url = os.getenv("TEST_DATABASE_URL")
if test_database_url:
    database_name = make_url(test_database_url).database or ""
    if "test" not in database_name.lower():
        raise RuntimeError(
            "TEST_DATABASE_URL must target a database whose name contains 'test'"
        )
    os.environ["DATABASE_URL"] = test_database_url


@pytest.fixture(scope="session")
def app_client():
    if not test_database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    from fastapi.testclient import TestClient

    from app.db import engine
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def integration_client(app_client):
    """Keep BUILD 001/002 integration tests authenticated as an administrator."""
    from types import SimpleNamespace

    from app.dependencies import require_admin, require_csrf, require_editor, require_viewer
    from app.main import app

    admin = SimpleNamespace(role="admin", is_active=True)
    for dependency in (require_viewer, require_editor, require_admin):
        app.dependency_overrides[dependency] = lambda: admin
    app.dependency_overrides[require_csrf] = lambda: None
    yield app_client
    for dependency in (require_viewer, require_editor, require_admin, require_csrf):
        app.dependency_overrides.pop(dependency, None)


@pytest.fixture(autouse=True)
def clean_integration_data():
    if not test_database_url:
        yield
        return

    from app.db import Base, engine

    table_names = [table.name for table in reversed(Base.metadata.sorted_tables)]
    quoted = ", ".join(f'"{name}"' for name in table_names)

    def truncate() -> None:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"
            )

    truncate()
    yield
    truncate()
