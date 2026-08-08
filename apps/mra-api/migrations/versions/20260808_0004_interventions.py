"""Add interventions and append-only operational timeline."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260808_0004"
down_revision = "20260807_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_environments_id_project", "environments", ["id", "project_id"])
    op.create_unique_constraint("uq_mra_objects_id_environment", "mra_objects", ["id", "environment_id"])
    op.execute("CREATE SEQUENCE intervention_code_seq START WITH 1 INCREMENT BY 1 NO CYCLE")
    op.create_table(
        "interventions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(32), server_default=sa.text("'INT-' || lpad(nextval('intervention_code_seq')::text, 6, '0')"), nullable=False),
        sa.Column("client_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_request_fingerprint", sa.CHAR(64), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mra_object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False), sa.Column("priority", sa.String(20), server_default="normal", nullable=False),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True)), sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_summary", sa.Text()), sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("code", name="uq_interventions_code"), sa.UniqueConstraint("client_request_id", name="uq_interventions_client_request_id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT", name="fk_interventions_project"), sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="RESTRICT", name="fk_interventions_environment"), sa.ForeignKeyConstraint(["mra_object_id"], ["mra_objects.id"], ondelete="RESTRICT", name="fk_interventions_object"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT", name="fk_interventions_created_by"), sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="RESTRICT", name="fk_interventions_assigned_user"),
        sa.ForeignKeyConstraint(["environment_id", "project_id"], ["environments.id", "environments.project_id"], ondelete="RESTRICT", name="fk_interventions_environment_project"),
        sa.ForeignKeyConstraint(["mra_object_id", "environment_id"], ["mra_objects.id", "mra_objects.environment_id"], ondelete="RESTRICT", name="fk_interventions_object_environment"),
        sa.CheckConstraint("status IN ('open','planned','in_progress','blocked','completed','cancelled')", name="ck_interventions_status"),
        sa.CheckConstraint("priority IN ('low','normal','high','urgent')", name="ck_interventions_priority"), sa.CheckConstraint("char_length(title) BETWEEN 1 AND 255", name="ck_interventions_title_length"),
        sa.CheckConstraint("char_length(description) <= 10000", name="ck_interventions_description_length"), sa.CheckConstraint("resolution_summary IS NULL OR char_length(resolution_summary) <= 5000", name="ck_interventions_resolution_length"), sa.CheckConstraint("version >= 1", name="ck_interventions_version"),
    )
    for name, cols in (("ix_interventions_created_id", ["created_at", "id"]), ("ix_interventions_scope", ["project_id", "environment_id", "mra_object_id"]), ("ix_interventions_status_priority", ["status", "priority"]), ("ix_interventions_assignee", ["assigned_user_id"]), ("ix_interventions_due_at", ["due_at"])):
        op.create_index(name, "interventions", cols)
    op.create_table(
        "intervention_events", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("intervention_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("event_type", sa.String(40), nullable=False), sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("actor_display_name_snapshot", sa.String(120), nullable=False), sa.Column("from_status", sa.String(20)), sa.Column("to_status", sa.String(20)), sa.Column("related_entity_id", postgresql.UUID(as_uuid=True)), sa.Column("note", sa.Text()), sa.Column("resolution_summary_snapshot", sa.Text()), sa.Column("command_id", postgresql.UUID(as_uuid=True)), sa.Column("command_fingerprint", sa.CHAR(64)), sa.Column("result_version", sa.Integer()), sa.Column("result_started_at", sa.DateTime(timezone=True)), sa.Column("result_completed_at", sa.DateTime(timezone=True)), sa.Column("result_cancelled_at", sa.DateTime(timezone=True)), sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("command_id", name="uq_intervention_events_command_id"), sa.ForeignKeyConstraint(["intervention_id"], ["interventions.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"), sa.CheckConstraint("event_type IN ('intervention_created','assignment_changed','status_changed','reopened','knowledge_linked','knowledge_unlinked')", name="ck_intervention_events_type"), sa.CheckConstraint("note IS NULL OR char_length(note) <= 1000", name="ck_intervention_events_note_length"), sa.CheckConstraint("resolution_summary_snapshot IS NULL OR char_length(resolution_summary_snapshot) <= 5000", name="ck_intervention_events_resolution_length")
    )
    op.create_index("ix_intervention_events_timeline", "intervention_events", ["intervention_id", "occurred_at", "id"])
    op.create_table(
        "intervention_knowledge_links", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("intervention_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("knowledge_card_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("usage_type", sa.String(40), nullable=False), sa.Column("note", sa.String(500), server_default="", nullable=False), sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("intervention_id", "knowledge_card_id", "usage_type", name="uq_intervention_knowledge_link"), sa.ForeignKeyConstraint(["intervention_id"], ["interventions.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["knowledge_card_id"], ["knowledge_cards.id"], ondelete="RESTRICT", name="fk_intervention_knowledge_links_card"), sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"), sa.CheckConstraint("usage_type IN ('diagnostic_reference','procedure_applied','solution_used')", name="ck_intervention_knowledge_links_usage"), sa.CheckConstraint("char_length(note) <= 500", name="ck_intervention_knowledge_links_note_length")
    )
    op.create_index("ix_intervention_knowledge_links_intervention_id", "intervention_knowledge_links", ["intervention_id"])
    op.create_index("ix_intervention_knowledge_links_knowledge_card_id", "intervention_knowledge_links", ["knowledge_card_id"])
    op.execute("""CREATE FUNCTION reject_intervention_event_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'intervention_events is append-only' USING ERRCODE = '55000'; END; $$""")
    op.execute("""CREATE TRIGGER intervention_events_append_only BEFORE UPDATE OR DELETE ON intervention_events FOR EACH ROW EXECUTE FUNCTION reject_intervention_event_mutation()""")


def downgrade() -> None:
    raise RuntimeError("The interventions migration is intentionally non-destructive; no data, tables, sequence, constraints, or triggers were removed.")
