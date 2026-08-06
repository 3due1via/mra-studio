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
def integration_client():
    if not test_database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")

    from fastapi.testclient import TestClient

    from app.db import engine
    from app.main import app

    with TestClient(app) as client:
        yield client


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
