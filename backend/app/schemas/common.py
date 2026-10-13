from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from app.models.service import Environment, ServiceStatus
from app.models.deployment import DeploymentStatus
from app.models.incident import IncidentSeverity, IncidentStatus

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class UserRead(ORMModel):
    id: UUID; name: str; email: str; is_active: bool; created_at: datetime
class AuthResponse(BaseModel):
    user: UserRead

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
class LoginRequest(BaseModel):
    email: str; password: str = Field(min_length=1, max_length=128)

class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    endpoint_url: HttpUrl
    environment: Environment = Environment.production
    monitoring_enabled: bool = True
    check_interval_seconds: int = Field(default=60, ge=15, le=86400)
    timeout_seconds: int = Field(default=5, ge=1, le=30)
    expected_status_code: int = Field(default=200, ge=100, le=599)
class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    endpoint_url: HttpUrl | None = None
    environment: Environment | None = None
    status: ServiceStatus | None = None
    monitoring_enabled: bool | None = None
    check_interval_seconds: int | None = Field(default=None, ge=15, le=86400)
    timeout_seconds: int | None = Field(default=None, ge=1, le=30)
    expected_status_code: int | None = Field(default=None, ge=100, le=599)
class ServiceRead(ORMModel):
    id: UUID; name: str; description: str | None; endpoint_url: str; environment: Environment; status: ServiceStatus
    monitoring_enabled: bool; check_interval_seconds: int; timeout_seconds: int; expected_status_code: int
    last_check_at: datetime | None; last_success_at: datetime | None; latest_response_ms: float | None
    created_at: datetime; updated_at: datetime
class HealthCheckRead(ORMModel):
    id: UUID; service_id: UUID; checked_at: datetime; success: bool; http_status_code: int | None; response_ms: float | None; failure_category: str | None
class ServiceAnalytics(BaseModel):
    from_time: datetime; to_time: datetime; total_checks: int; successful_checks: int; failed_checks: int
    uptime_percent: float | None; average_response_ms: float | None; min_response_ms: float | None
    max_response_ms: float | None; p95_response_ms: float | None; checks: list[HealthCheckRead]

class DeploymentCreate(BaseModel):
    service_id: UUID; version: str = Field(min_length=1, max_length=120); branch: str | None = None
    commit_sha: str | None = Field(default=None, max_length=64); environment: str = Field(min_length=1, max_length=32)
    status: DeploymentStatus; deployed_at: datetime | None = None; details: dict | None = None
class DeploymentRead(ORMModel):
    id: UUID; service_id: UUID; version: str; branch: str | None; commit_sha: str | None; environment: str; status: DeploymentStatus; deployed_at: datetime | None; details: dict | None; created_at: datetime

class IncidentCreate(BaseModel):
    service_id: UUID; title: str = Field(min_length=1, max_length=200); description: str | None = None
    severity: IncidentSeverity; status: IncidentStatus = IncidentStatus.open
class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200); description: str | None = None
    severity: IncidentSeverity | None = None; status: IncidentStatus | None = None
class IncidentRead(ORMModel):
    id: UUID; service_id: UUID; title: str; description: str | None; severity: IncidentSeverity; status: IncidentStatus; created_at: datetime; updated_at: datetime; resolved_at: datetime | None
