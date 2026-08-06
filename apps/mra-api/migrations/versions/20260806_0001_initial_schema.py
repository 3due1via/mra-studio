"""Create the initial MRA Studio schema on a new PostgreSQL database."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260806_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    _create_knowledge_cards()
    _create_projects()
    _create_knowledge_relations()
    _create_knowledge_revisions()
    _create_environments()
    _create_mra_objects()


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def _create_knowledge_cards() -> None:
    op.create_table(
        "knowledge_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.String(30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("symptoms", sa.Text(), nullable=False),
        sa.Column("causes", sa.Text(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column("procedure", sa.Text(), nullable=False),
        sa.Column("tools", sa.Text(), nullable=False),
        sa.Column("safety", sa.Text(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("code", "title", "category", "status"):
        op.create_index(
            f"ix_knowledge_cards_{column}",
            "knowledge_cards",
            [column],
            unique=column == "code",
        )


def _create_projects() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("project_type", sa.String(80), nullable=False),
        sa.Column("customer", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("name", "project_type", "status"):
        op.create_index(f"ix_projects_{column}", "projects", [column])


def _create_knowledge_relations() -> None:
    op.create_table(
        "knowledge_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(40), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["knowledge_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "target_id", "relation_type", name="uq_knowledge_relation"),
    )
    for column in ("source_id", "target_id", "relation_type"):
        op.create_index(f"ix_knowledge_relations_{column}", "knowledge_relations", [column])


def _create_knowledge_revisions() -> None:
    op.create_table(
        "knowledge_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["knowledge_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "revision_number", name="uq_knowledge_revision_number"),
    )
    op.create_index("ix_knowledge_revisions_card_id", "knowledge_revisions", ["card_id"])
    op.create_index("ix_knowledge_revisions_revision_number", "knowledge_revisions", ["revision_number"])


def _create_environments() -> None:
    op.create_table(
        "environments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("environment_type", sa.String(80), nullable=False),
        sa.Column("area_m2", sa.String(30), nullable=False),
        sa.Column("height_m", sa.String(30), nullable=False),
        sa.Column("width_m", sa.String(30), nullable=False),
        sa.Column("length_m", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("project_id", "name", "environment_type"):
        op.create_index(f"ix_environments_{column}", "environments", [column])


def _create_mra_objects() -> None:
    op.create_table(
        "mra_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("brand", sa.String(120), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("serial_number", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("environment_id", "category", "name", "status"):
        op.create_index(f"ix_mra_objects_{column}", "mra_objects", [column])


def downgrade() -> None:
    raise RuntimeError(
        "The initial MRA Studio baseline is intentionally irreversible. "
        "No tables or data were removed. Restore from a verified backup "
        "or rebuild an empty development database instead."
    )
