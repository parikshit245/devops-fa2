"""monitoring configuration and health history"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_monitoring"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("services", sa.Column("monitoring_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("services", sa.Column("check_interval_seconds", sa.Integer(), nullable=False, server_default="60"))
    op.add_column("services", sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("services", sa.Column("expected_status_code", sa.Integer(), nullable=False, server_default="200"))
    op.add_column("services", sa.Column("last_check_at", sa.DateTime(timezone=True)))
    op.add_column("services", sa.Column("last_success_at", sa.DateTime(timezone=True)))
    op.add_column("services", sa.Column("latest_response_ms", sa.Float()))
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE servicestatus ADD VALUE IF NOT EXISTS 'unknown'")
        op.execute("ALTER TYPE servicestatus ADD VALUE IF NOT EXISTS 'paused'")
    op.create_table("health_checks", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False), sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False), sa.Column("success", sa.Boolean(), nullable=False), sa.Column("http_status_code", sa.Integer()), sa.Column("response_ms", sa.Float()), sa.Column("failure_category", sa.String(32)))
    op.create_index("ix_health_checks_service_checked_at", "health_checks", ["service_id", "checked_at"])

def downgrade():
    op.drop_index("ix_health_checks_service_checked_at", table_name="health_checks")
    op.drop_table("health_checks")
    for column in ("latest_response_ms", "last_success_at", "last_check_at", "expected_status_code", "timeout_seconds", "check_interval_seconds", "monitoring_enabled"): op.drop_column("services", column)
