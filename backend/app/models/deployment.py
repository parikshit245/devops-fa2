from datetime import datetime
from enum import StrEnum
from uuid import UUID
from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, Timestamped, uuid_column

class DeploymentStatus(StrEnum):
    success = "success"; failed = "failed"; in_progress = "in_progress"

class Deployment(Base, Timestamped):
    __tablename__ = "deployments"
    __table_args__ = (Index("ix_deployments_owner_id", "owner_id"),)
    id: Mapped[UUID] = uuid_column()
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String(120), nullable=False)
    branch: Mapped[str | None] = mapped_column(String(255))
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[DeploymentStatus] = mapped_column(Enum(DeploymentStatus), nullable=False)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict | None] = mapped_column(JSON)
    owner = relationship("User", back_populates="deployments")
    service = relationship("MonitoredService", back_populates="deployments")
