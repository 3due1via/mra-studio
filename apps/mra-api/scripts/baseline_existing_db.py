"""Validate an existing MRA schema before explicitly stamping the baseline.

This tool never creates, alters, or drops domain tables. Without ``--stamp`` it
is fully read-only. With ``--stamp`` it writes only Alembic's version marker,
and only after the existing schema matches the SQLAlchemy baseline exactly.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
import sqlalchemy as sa
from sqlalchemy import MetaData
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.schema import ForeignKeyConstraint, UniqueConstraint

from app import models  # noqa: F401 - registers all model tables
from app.config import settings
from app.db import Base

BASELINE_REVISION = "20260806_0001"
ALEMBIC_TABLE = "alembic_version"
BASELINE_TABLES = {
    "knowledge_cards",
    "knowledge_relations",
    "knowledge_revisions",
    "projects",
    "environments",
    "mra_objects",
}


class SchemaDriftError(RuntimeError):
    """Raised when an existing database does not match the baseline schema."""


def _type_signature(connection: Connection, column_type: sa.types.TypeEngine) -> str:
    compiled = connection.dialect.type_compiler.process(column_type)
    return " ".join(compiled.upper().split())


def _foreign_keys(table: sa.Table) -> set[tuple]:
    return {
        (
            tuple(constraint.column_keys),
            constraint.referred_table.name,
            tuple(element.column.name for element in constraint.elements),
            (constraint.ondelete or "").upper(),
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def _actual_foreign_keys(inspector: sa.Inspector, table_name: str) -> set[tuple]:
    return {
        (
            tuple(item["constrained_columns"]),
            item["referred_table"],
            tuple(item["referred_columns"]),
            (item.get("options", {}).get("ondelete") or "").upper(),
        )
        for item in inspector.get_foreign_keys(table_name)
    }


def _unique_columns(table: sa.Table) -> set[tuple[str, ...]]:
    return {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _actual_unique_columns(
    inspector: sa.Inspector, table_name: str
) -> set[tuple[str, ...]]:
    return {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints(table_name)
    }


def _indexes(table: sa.Table) -> dict[str, tuple[tuple[str, ...], bool]]:
    return {
        index.name: (tuple(index.columns.keys()), bool(index.unique))
        for index in table.indexes
    }


def _actual_indexes(
    inspector: sa.Inspector, table_name: str
) -> dict[str, tuple[tuple[str, ...], bool]]:
    return {
        item["name"]: (tuple(item["column_names"]), bool(item["unique"]))
        for item in inspector.get_indexes(table_name)
        if not item.get("duplicates_constraint")
    }


def schema_drift(
    connection: Connection,
    metadata: MetaData = Base.metadata,
) -> list[str]:
    """Return a deterministic list of differences without changing the database."""

    inspector = sa.inspect(connection)
    expected_names = set(metadata.tables)
    actual_names = set(inspector.get_table_names()) - {ALEMBIC_TABLE}
    differences: list[str] = []

    missing_tables = sorted(expected_names - actual_names)
    extra_tables = sorted(actual_names - expected_names)
    if missing_tables:
        differences.append(f"missing tables: {', '.join(missing_tables)}")
    if extra_tables:
        differences.append(f"unexpected tables: {', '.join(extra_tables)}")

    for table_name in sorted(expected_names & actual_names):
        table = metadata.tables[table_name]
        actual_columns = {item["name"]: item for item in inspector.get_columns(table_name)}
        expected_columns = {column.name: column for column in table.columns}

        missing_columns = sorted(set(expected_columns) - set(actual_columns))
        extra_columns = sorted(set(actual_columns) - set(expected_columns))
        if missing_columns:
            differences.append(
                f"{table_name}: missing columns: {', '.join(missing_columns)}"
            )
        if extra_columns:
            differences.append(
                f"{table_name}: unexpected columns: {', '.join(extra_columns)}"
            )

        for column_name in sorted(set(expected_columns) & set(actual_columns)):
            expected = expected_columns[column_name]
            actual = actual_columns[column_name]
            expected_type = _type_signature(connection, expected.type)
            actual_type = _type_signature(connection, actual["type"])
            if expected_type != actual_type:
                differences.append(
                    f"{table_name}.{column_name}: type {actual_type}, expected {expected_type}"
                )
            if bool(actual["nullable"]) != bool(expected.nullable):
                differences.append(
                    f"{table_name}.{column_name}: nullable={actual['nullable']}, "
                    f"expected {expected.nullable}"
                )

        expected_pk = tuple(table.primary_key.columns.keys())
        actual_pk = tuple(inspector.get_pk_constraint(table_name)["constrained_columns"])
        if actual_pk != expected_pk:
            differences.append(
                f"{table_name}: primary key {actual_pk}, expected {expected_pk}"
            )

        expected_fks = _foreign_keys(table)
        actual_fks = _actual_foreign_keys(inspector, table_name)
        if actual_fks != expected_fks:
            differences.append(
                f"{table_name}: foreign keys {sorted(actual_fks)!r}, "
                f"expected {sorted(expected_fks)!r}"
            )

        expected_uniques = _unique_columns(table)
        actual_uniques = _actual_unique_columns(inspector, table_name)
        if actual_uniques != expected_uniques:
            differences.append(
                f"{table_name}: unique constraints {sorted(actual_uniques)!r}, "
                f"expected {sorted(expected_uniques)!r}"
            )

        expected_indexes = _indexes(table)
        actual_indexes = _actual_indexes(inspector, table_name)
        if actual_indexes != expected_indexes:
            differences.append(
                f"{table_name}: indexes {actual_indexes!r}, expected {expected_indexes!r}"
            )

    return differences


def validate_existing_schema(
    connection: Connection,
    metadata: MetaData = Base.metadata,
) -> None:
    differences = schema_drift(connection, metadata)
    if differences:
        details = "\n - ".join(differences)
        raise SchemaDriftError(f"Schema drift detected:\n - {details}")


def _current_revision(connection: Connection) -> str | None:
    if ALEMBIC_TABLE not in sa.inspect(connection).get_table_names():
        return None
    return connection.scalar(sa.text("SELECT version_num FROM alembic_version"))


def baseline_existing_database(engine: Engine, *, stamp: bool = False) -> None:
    """Validate an existing schema and optionally stamp only the Alembic marker."""

    with engine.connect() as connection:
        baseline_metadata = MetaData()
        for table_name in sorted(BASELINE_TABLES):
            Base.metadata.tables[table_name].to_metadata(baseline_metadata)
        validate_existing_schema(connection, baseline_metadata)
        current_revision = _current_revision(connection)

    if current_revision not in (None, BASELINE_REVISION):
        raise SchemaDriftError(
            f"Database is already stamped with unexpected revision {current_revision!r}."
        )

    if not stamp or current_revision == BASELINE_REVISION:
        return

    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option(
        "script_location", str(config_path.parent / "migrations")
    )
    config.set_main_option(
        "sqlalchemy.url", engine.url.render_as_string(hide_password=False)
    )
    command.stamp(config, BASELINE_REVISION)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify an existing MRA database before baseline stamping."
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="After successful read-only validation, stamp the Alembic baseline.",
    )
    args = parser.parse_args()

    engine = sa.create_engine(settings.database_url, pool_pre_ping=True)
    try:
        baseline_existing_database(engine, stamp=args.stamp)
    except (SchemaDriftError, sa.exc.SQLAlchemyError) as exc:
        print(f"Baseline refused: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    if args.stamp:
        print(f"Schema compatible. Database stamped at {BASELINE_REVISION}.")
    else:
        print("Schema compatible. No changes made; rerun with --stamp to baseline it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
