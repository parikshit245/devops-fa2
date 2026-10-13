from datetime import datetime
from enum import StrEnum
from uuid import UUID
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Index, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, Timestamped, uuid_column

class Environment(StrEnum):
    development = "development"; staging = "staging"; production = "production"
class ServiceStatus(StrEnum):
    unknown = "unknown"; operational = "operational"; degraded = "degraded"; down = "down"; paused = "paused"

class MonitoredService(Base, Timestamped):
    __tablename__ = "services"
    __table_args__ = (Index("ix_services_owner_id", "owner_id"),)
    id: Mapped[UUID] = uuid_column()
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    endpoint_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    environment: Mapped[Environment] = mapped_column(Enum(Environment), default=Environment.production, nullable=False)
    status: Mapped[ServiceStatus] = mapped_column(Enum(ServiceStatus), default=ServiceStatus.operational, nullable=False)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    expected_status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_response_ms: Mapped[float | None] = mapped_column(Float)
    owner = relationship("User", back_populates="services")
    deployments = relationship("Deployment", back_populates="service", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="service", cascade="all, delete-orphan")
    checks = relationship("HealthCheck", back_populates="service", cascade="all, delete-orphan")
