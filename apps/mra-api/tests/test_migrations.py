from concurrent.futures import ThreadPoolExecutor
import threading

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa

from app.db import Base, SessionLocal, engine
from app.models import KnowledgeCard, Project
from app.repositories.knowledge_repository import SqlAlchemyKnowledgeRepository
from app.repositories.knowledge_revision_repository import (
    SqlAlchemyKnowledgeRevisionRepository,
)
from app.services.knowledge_revision_service import KnowledgeRevisionService
from scripts.baseline_existing_db import (
    BASELINE_REVISION,
    SchemaDriftError,
    baseline_existing_database,
    validate_existing_schema,
)

EXPECTED_TABLES = {
    "knowledge_cards",
    "knowledge_relations",
    "knowledge_revisions",
    "projects",
    "environments",
    "mra_objects",
}


def test_00_alembic_upgrades_empty_database(integration_client):
    engine.dispose()
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP SCHEMA public CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA public")

    command.upgrade(Config("alembic.ini"), "head")

    inspector = sa.inspect(engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())


def test_alembic_created_expected_schema(integration_client):
    inspector = sa.inspect(engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())

    with engine.connect() as connection:
        assert connection.scalar(
            sa.text("SELECT version_num FROM alembic_version")
        ) == BASELINE_REVISION
        validate_existing_schema(connection)

    health = integration_client.get("/health")
    assert health.status_code == 200
    assert health.json()["database"] == "reachable"

    revision_uniques = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("knowledge_revisions")
    }
    assert ("card_id", "revision_number") in revision_uniques


def test_compatible_schema_is_accepted(integration_client):
    baseline_existing_database(engine, stamp=False)


def test_compatible_unversioned_schema_can_be_stamped(integration_client):
    with engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM alembic_version"))

    try:
        baseline_existing_database(engine, stamp=True)
        with engine.connect() as connection:
            assert connection.scalar(
                sa.text("SELECT version_num FROM alembic_version")
            ) == BASELINE_REVISION
    finally:
        with engine.begin() as connection:
            current = connection.scalar(
                sa.text("SELECT version_num FROM alembic_version")
            )
            if current is None:
                connection.execute(
                    sa.text(
                        "INSERT INTO alembic_version (version_num) VALUES (:revision)"
                    ),
                    {"revision": BASELINE_REVISION},
                )


def test_schema_drift_is_rejected(integration_client):
    drifted = sa.MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(drifted)
    drifted.tables["knowledge_cards"].append_column(
        sa.Column("missing_required_column", sa.Text(), nullable=False)
    )

    with engine.connect() as connection, pytest.raises(
        SchemaDriftError, match="missing columns"
    ):
        validate_existing_schema(connection, drifted)


def test_initial_downgrade_is_non_destructive(integration_client):
    with SessionLocal() as session:
        project = Project(name="Downgrade sentinel", project_type="Test")
        session.add(project)
        session.commit()

    config = Config("alembic.ini")
    with pytest.raises(RuntimeError, match="intentionally irreversible"):
        command.downgrade(config, "base")

    inspector = sa.inspect(engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())
    with SessionLocal() as session:
        assert session.scalar(
            sa.select(sa.func.count()).select_from(Project)
        ) == 1


def test_concurrent_revision_numbers_are_sequential(integration_client):
    with SessionLocal() as session:
        card = KnowledgeCard(
            code="KC-CONCURRENCY-001",
            title="Concurrency",
            category="Test",
        )
        session.add(card)
        session.commit()
        card_id = card.id

    barrier = threading.Barrier(2)

    def record_revision() -> int:
        with SessionLocal() as session:
            knowledge_repository = SqlAlchemyKnowledgeRepository(session)
            service = KnowledgeRevisionService(
                SqlAlchemyKnowledgeRevisionRepository(session),
                knowledge_repository,
            )
            current_card = knowledge_repository.get(card_id)
            assert current_card is not None
            barrier.wait(timeout=10)
            revision = service.record(current_card, action="update")
            knowledge_repository.commit()
            return revision.revision_number

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(record_revision) for _ in range(2)]
        numbers = sorted(future.result(timeout=20) for future in futures)

    assert numbers == [1, 2]
