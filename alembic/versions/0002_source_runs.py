"""add source runs

Revision ID: 0002_source_runs
Revises: 0001_initial
Create Date: 2026-02-06
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_source_runs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    source_run_status = sa.Enum("success", "failure", "skipped", name="sourcerunstatus")
    source_run_status.create(bind, checkfirst=True)

    op.create_table(
        "source_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("trigger_type", sa.String(length=64), nullable=False, server_default="scheduled"),
        sa.Column("status", source_run_status, nullable=False, server_default="success"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("items_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_source_runs_source_started", "source_runs", ["source_id", "started_at"])


def downgrade() -> None:
    op.drop_index("ix_source_runs_source_started", table_name="source_runs")
    op.drop_table("source_runs")
    bind = op.get_bind()
    sa.Enum(name="sourcerunstatus").drop(bind, checkfirst=True)
