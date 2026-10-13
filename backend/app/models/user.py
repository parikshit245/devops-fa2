from uuid import UUID
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, Timestamped, uuid_column

class User(Base, Timestamped):
    __tablename__ = "users"
    id: Mapped[UUID] = uuid_column()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    services = relationship("MonitoredService", back_populates="owner", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="owner", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="owner", cascade="all, delete-orphan")
