"""initial schema"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    environment = sa.Enum("development", "staging", "production", name="environment")
    service_status = sa.Enum("operational", "degraded", "down", name="servicestatus")
    deployment_status = sa.Enum("success", "failed", "in_progress", name="deploymentstatus")
    incident_severity = sa.Enum("critical", "major", "minor", name="incidentseverity")
    incident_status = sa.Enum("open", "investigating", "resolved", name="incidentstatus")
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("users", sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("email", sa.String(320), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("services", sa.Column("id", uuid, primary_key=True), sa.Column("owner_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("description", sa.Text()), sa.Column("endpoint_url", sa.String(2048), nullable=False), sa.Column("environment", environment, nullable=False), sa.Column("status", service_status, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_services_owner_id", "services", ["owner_id"])
    op.create_table("deployments", sa.Column("id", uuid, primary_key=True), sa.Column("owner_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("service_id", uuid, sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False), sa.Column("version", sa.String(120), nullable=False), sa.Column("branch", sa.String(255)), sa.Column("commit_sha", sa.String(64)), sa.Column("environment", sa.String(32), nullable=False), sa.Column("status", deployment_status, nullable=False), sa.Column("deployed_at", sa.DateTime(timezone=True)), sa.Column("details", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_deployments_owner_id", "deployments", ["owner_id"])
    op.create_table("incidents", sa.Column("id", uuid, primary_key=True), sa.Column("owner_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("service_id", uuid, sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("severity", incident_severity, nullable=False), sa.Column("status", incident_status, nullable=False), sa.Column("resolved_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_incidents_owner_id", "incidents", ["owner_id"])

def downgrade() -> None:
    for name in ("incidents", "deployments", "services", "users"): op.drop_table(name)
    for name in ("incidentstatus", "incidentseverity", "deploymentstatus", "servicestatus", "environment"): sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
