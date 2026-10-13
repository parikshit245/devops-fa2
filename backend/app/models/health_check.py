from datetime import datetime
from enum import StrEnum
from uuid import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, uuid_column

class FailureCategory(StrEnum):
    http_status = "http_status"; timeout = "timeout"; connection = "connection"; dns = "dns"; tls = "tls"; blocked = "blocked"; unknown = "unknown"

class HealthCheck(Base):
    __tablename__ = "health_checks"
    __table_args__ = (Index("ix_health_checks_service_checked_at", "service_id", "checked_at"),)
    id: Mapped[UUID] = uuid_column()
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    http_status_code: Mapped[int | None] = mapped_column(Integer)
    response_ms: Mapped[float | None] = mapped_column(Float)
    failure_category: Mapped[str | None] = mapped_column(String(32))
    service = relationship("MonitoredService", back_populates="checks")
