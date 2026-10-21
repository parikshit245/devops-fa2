import time
from datetime import datetime, timezone
import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.metrics import monitoring_check_duration_seconds, monitoring_checks_total
from app.models.health_check import HealthCheck, FailureCategory
from app.models.service import MonitoredService, ServiceStatus
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.monitoring.ssrf import validate_public_url

async def run_check(service: MonitoredService, db: AsyncSession, client: httpx.AsyncClient) -> HealthCheck:
    check_started = time.perf_counter()
    checked_at = datetime.now(timezone.utc)
    success = False; code = None; response_ms = None; category: str | None = None
    try:
        await validate_public_url(service.endpoint_url)
        started = time.perf_counter()
        response = await client.get(service.endpoint_url, timeout=service.timeout_seconds, follow_redirects=False)
        response_ms = round((time.perf_counter() - started) * 1000, 2)
        code = response.status_code
        success = code == service.expected_status_code
        if not success: category = FailureCategory.http_status
    except HTTPException: category = FailureCategory.blocked
    except httpx.TimeoutException: category = FailureCategory.timeout
    except httpx.ConnectError: category = FailureCategory.connection
    except httpx.TransportError: category = FailureCategory.unknown
    check = HealthCheck(service_id=service.id, checked_at=checked_at, success=success, http_status_code=code, response_ms=response_ms, failure_category=category)
    db.add(check)
    await db.flush()
    service.last_check_at = checked_at
    if success:
        service.last_success_at = checked_at; service.latest_response_ms = response_ms; service.status = ServiceStatus.operational
        incident = await db.scalar(select(Incident).where(Incident.service_id == service.id, Incident.owner_id == service.owner_id, Incident.status != IncidentStatus.resolved, Incident.description.like("[auto]%")))
        if incident: incident.status = IncidentStatus.resolved; incident.resolved_at = checked_at
    else:
        failures = list((await db.scalars(select(HealthCheck).where(HealthCheck.service_id == service.id, HealthCheck.success.is_(False)).order_by(HealthCheck.checked_at.desc()).limit(2))).all())
        service.status = ServiceStatus.down if len(failures) >= 2 else ServiceStatus.degraded
        if len(failures) >= 2:
            open_incident = await db.scalar(select(Incident).where(Incident.service_id == service.id, Incident.owner_id == service.owner_id, Incident.status != IncidentStatus.resolved, Incident.description.like("[auto]%")))
            if not open_incident: db.add(Incident(owner_id=service.owner_id, service_id=service.id, title=f"{service.name} is down", description="[auto] Consecutive health checks failed.", severity=IncidentSeverity.major))
    await db.commit(); await db.refresh(check)
    outcome = "success" if success else "failure"
    monitoring_checks_total.labels(outcome=outcome).inc()
    monitoring_check_duration_seconds.observe(time.perf_counter() - check_started)
    return check
