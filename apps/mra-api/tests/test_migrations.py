from concurrent.futures import ThreadPoolExecutor
import threading
import uuid

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
    "users",
    "auth_sessions",
    "knowledge_cards",
    "knowledge_relations",
    "knowledge_revisions",
    "projects",
    "environments",
    "mra_objects",
    "audit_events",
}
HEAD_REVISION = "20260807_0003"


def _assert_audit_trigger_operational() -> None:
    event_id = str(uuid.uuid4()); request_id = str(uuid.uuid4())
    with engine.begin() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE tgname = 'audit_events_append_only' AND tgenabled = 'O'")) == 1
        connection.execute(sa.text("INSERT INTO audit_events (id, action, entity_type, outcome, request_id) VALUES (:id, 'project.created', 'project', 'success', :request_id)"), {"id": event_id, "request_id": request_id})
    with pytest.raises(sa.exc.DBAPIError), engine.begin() as connection:
        connection.execute(sa.text("UPDATE audit_events SET action = 'project.updated' WHERE id = :id"), {"id": event_id})
    with pytest.raises(sa.exc.DBAPIError), engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM audit_events WHERE id = :id"), {"id": event_id})


def test_00_alembic_upgrades_empty_database(integration_client):
    engine.dispose()
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP SCHEMA public CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA public")

    config = Config("alembic.ini")
    command.upgrade(config, BASELINE_REVISION)
    baseline_tables = set(sa.inspect(engine).get_table_names())
    assert "users" not in baseline_tables
    assert "auth_sessions" not in baseline_tables
    command.upgrade(config, "20260807_0002")
    assert "audit_events" not in set(sa.inspect(engine).get_table_names())
    command.upgrade(config, "head")
    _assert_audit_trigger_operational()

    inspector = sa.inspect(engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())


def test_01_upgrade_build_003_schema_to_audit_head_enables_trigger(integration_client):
    engine.dispose()
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP SCHEMA public CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA public")
    config = Config("alembic.ini")
    command.upgrade(config, "20260807_0002")
    assert "audit_events" not in set(sa.inspect(engine).get_table_names())
    command.upgrade(config, "head")
    _assert_audit_trigger_operational()


def test_alembic_created_expected_schema(integration_client):
    inspector = sa.inspect(engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())

    with engine.connect() as connection:
        assert connection.scalar(
            sa.text("SELECT version_num FROM alembic_version")
        ) == HEAD_REVISION
        validate_existing_schema(connection)
    _assert_audit_trigger_operational()

    health = integration_client.get("/health")
    assert health.status_code == 200
    assert health.json()["database"] == "reachable"

    revision_uniques = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("knowledge_revisions")
    }
    assert ("card_id", "revision_number") in revision_uniques


def test_compatible_schema_is_accepted(integration_client):
    with engine.connect() as connection:
        validate_existing_schema(connection)


def test_current_head_is_not_misstamped_as_historical_baseline(integration_client):
    with pytest.raises(SchemaDriftError, match="unexpected tables"):
        baseline_existing_database(engine, stamp=True)


def test_legacy_baseline_stamp_then_upgrade_preserves_data(integration_client):
    engine.dispose()
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP SCHEMA public CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA public")
    config = Config("alembic.ini")
    command.upgrade(config, BASELINE_REVISION)
    sentinel_id = "00000000-0000-0000-0000-000000000003"
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO projects (id, name, project_type, customer, description, status, progress) "
                "VALUES (:id, 'Legacy sentinel', 'Test', '', '', 'draft', 0)"
            ),
            {"id": sentinel_id},
        )
        connection.execute(sa.text("DELETE FROM alembic_version"))

    baseline_existing_database(engine, stamp=True)
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == HEAD_REVISION
        assert connection.scalar(sa.text("SELECT name FROM projects WHERE id = :id"), {"id": sentinel_id}) == "Legacy sentinel"
        validate_existing_schema(connection)
    _assert_audit_trigger_operational()


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
    with pytest.raises(RuntimeError, match="intentionally non-destructive"):
        command.downgrade(config, "base")

    inspector = sa.inspect(engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())
    with SessionLocal() as session:
        assert session.scalar(
            sa.select(sa.func.count()).select_from(Project)
        ) == 1
    _assert_audit_trigger_operational()


def test_audit_events_are_database_append_only(integration_client):
    event_id = "00000000-0000-0000-0000-000000000004"
    request_id = "00000000-0000-0000-0000-000000000005"
    with engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO audit_events (id, action, entity_type, outcome, request_id) VALUES (:id, 'project.created', 'project', 'success', :request_id)"), {"id": event_id, "request_id": request_id})
    with pytest.raises(sa.exc.DBAPIError), engine.begin() as connection:
        connection.execute(sa.text("UPDATE audit_events SET action = 'project.updated' WHERE id = :id"), {"id": event_id})
    with pytest.raises(sa.exc.DBAPIError), engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM audit_events WHERE id = :id"), {"id": event_id})
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM pg_trigger WHERE tgname = 'audit_events_append_only' AND tgenabled = 'O'")) == 1


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
