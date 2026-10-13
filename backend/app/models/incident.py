from datetime import datetime
from enum import StrEnum
from uuid import UUID
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, Timestamped, uuid_column

class IncidentSeverity(StrEnum):
    critical = "critical"; major = "major"; minor = "minor"
class IncidentStatus(StrEnum):
    open = "open"; investigating = "investigating"; resolved = "resolved"

class Incident(Base, Timestamped):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_owner_id", "owner_id"),)
    id: Mapped[UUID] = uuid_column()
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[IncidentSeverity] = mapped_column(Enum(IncidentSeverity), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus), default=IncidentStatus.open, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    owner = relationship("User", back_populates="incidents")
    service = relationship("MonitoredService", back_populates="incidents")
