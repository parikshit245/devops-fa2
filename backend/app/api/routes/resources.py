from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import current_user
from app.db.session import get_db
from app.models import Deployment, Incident, MonitoredService, User
from app.models.incident import IncidentStatus
from app.schemas.common import DeploymentCreate, DeploymentRead, HealthCheckRead, IncidentCreate, IncidentRead, IncidentUpdate, ServiceAnalytics, ServiceCreate, ServiceRead, ServiceUpdate
from app.models.health_check import HealthCheck
from app.monitoring.checker import run_check
import httpx
from datetime import timedelta, timezone

router = APIRouter(prefix="/api/v1", tags=["resources"])
async def owned_service(service_id: UUID, user: User, db: AsyncSession) -> MonitoredService:
    service = await db.scalar(select(MonitoredService).where(MonitoredService.id == service_id, MonitoredService.owner_id == user.id))
    if not service: raise HTTPException(status_code=404, detail="Service not found")
    return service

@router.get("/services", response_model=list[ServiceRead])
async def list_services(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)): return list((await db.scalars(select(MonitoredService).where(MonitoredService.owner_id == user.id).limit(100))).all())
@router.post("/services", response_model=ServiceRead, status_code=201)
async def create_service(payload: ServiceCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    values = payload.model_dump()
    values["endpoint_url"] = str(values["endpoint_url"])
    service = MonitoredService(owner_id=user.id, **values); db.add(service); await db.commit(); await db.refresh(service); return service
@router.get("/services/{service_id}", response_model=ServiceRead)
async def get_service(service_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)): return await owned_service(service_id, user, db)
@router.patch("/services/{service_id}", response_model=ServiceRead)
async def update_service(service_id: UUID, payload: ServiceUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    service = await owned_service(service_id, user, db)
    values = payload.model_dump(exclude_unset=True)
    if "endpoint_url" in values: values["endpoint_url"] = str(values["endpoint_url"])
    for key, value in values.items(): setattr(service, key, value)
    await db.commit(); await db.refresh(service); return service
@router.delete("/services/{service_id}", status_code=204)
async def delete_service(service_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    service = await owned_service(service_id, user, db); await db.delete(service); await db.commit()

@router.post("/services/{service_id}/check", response_model=HealthCheckRead)
async def manual_check(service_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    service = await owned_service(service_id, user, db)
    async with httpx.AsyncClient() as client:
        return await run_check(service, db, client)

@router.get("/services/{service_id}/checks", response_model=list[HealthCheckRead])
async def list_checks(service_id: UUID, hours: int = 24, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    service = await owned_service(service_id, user, db)
    since = datetime.now(timezone.utc) - timedelta(hours=min(max(hours, 1), 720))
    return list((await db.scalars(select(HealthCheck).where(HealthCheck.service_id == service.id, HealthCheck.checked_at >= since).order_by(HealthCheck.checked_at.desc()).limit(500))).all())

@router.get("/services/{service_id}/analytics", response_model=ServiceAnalytics)
async def service_analytics(service_id: UUID, days: int = 1, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    service = await owned_service(service_id, user, db)
    to_time = datetime.now(timezone.utc); from_time = to_time - timedelta(days=min(max(days, 1), 30))
    checks = list((await db.scalars(select(HealthCheck).where(HealthCheck.service_id == service.id, HealthCheck.checked_at >= from_time, HealthCheck.checked_at <= to_time).order_by(HealthCheck.checked_at.desc()).limit(1000))).all())
    durations = sorted([check.response_ms for check in checks if check.response_ms is not None])
    percentile = durations[min(len(durations) - 1, round(0.95 * (len(durations) - 1)))] if durations else None
    return ServiceAnalytics(from_time=from_time, to_time=to_time, total_checks=len(checks), successful_checks=sum(c.success for c in checks), failed_checks=sum(not c.success for c in checks), uptime_percent=round(sum(c.success for c in checks) / len(checks) * 100, 2) if checks else None, average_response_ms=round(sum(durations) / len(durations), 2) if durations else None, min_response_ms=min(durations) if durations else None, max_response_ms=max(durations) if durations else None, p95_response_ms=percentile, checks=checks[:200])

@router.get("/deployments", response_model=list[DeploymentRead])
async def list_deployments(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)): return list((await db.scalars(select(Deployment).where(Deployment.owner_id == user.id).limit(100))).all())
@router.post("/deployments", response_model=DeploymentRead, status_code=201)
async def create_deployment(payload: DeploymentCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await owned_service(payload.service_id, user, db)
    deployment = Deployment(owner_id=user.id, **payload.model_dump()); db.add(deployment); await db.commit(); await db.refresh(deployment); return deployment
@router.get("/deployments/{deployment_id}", response_model=DeploymentRead)
async def get_deployment(deployment_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    deployment = await db.scalar(select(Deployment).where(Deployment.id == deployment_id, Deployment.owner_id == user.id))
    if not deployment: raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment

@router.get("/incidents", response_model=list[IncidentRead])
async def list_incidents(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)): return list((await db.scalars(select(Incident).where(Incident.owner_id == user.id).limit(100))).all())
@router.post("/incidents", response_model=IncidentRead, status_code=201)
async def create_incident(payload: IncidentCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await owned_service(payload.service_id, user, db)
    incident = Incident(owner_id=user.id, **payload.model_dump()); db.add(incident); await db.commit(); await db.refresh(incident); return incident
@router.get("/incidents/{incident_id}", response_model=IncidentRead)
async def get_incident(incident_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    incident = await db.scalar(select(Incident).where(Incident.id == incident_id, Incident.owner_id == user.id))
    if not incident: raise HTTPException(status_code=404, detail="Incident not found")
    return incident
@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
async def update_incident(incident_id: UUID, payload: IncidentUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    incident = await get_incident(incident_id, user, db)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(incident, key, value)
    if incident.status == IncidentStatus.resolved and incident.resolved_at is None: incident.resolved_at = datetime.now(timezone.utc)
    if incident.status != IncidentStatus.resolved: incident.resolved_at = None
    await db.commit(); await db.refresh(incident); return incident
