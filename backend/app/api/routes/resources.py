from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
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
    conditions = (HealthCheck.service_id == service.id, HealthCheck.checked_at >= from_time, HealthCheck.checked_at <= to_time)
    summary = (await db.execute(select(
        func.count(HealthCheck.id),
        func.coalesce(func.sum(case((HealthCheck.success.is_(True), 1), else_=0)), 0),
        func.avg(HealthCheck.response_ms),
        func.min(HealthCheck.response_ms),
        func.max(HealthCheck.response_ms),
    ).where(*conditions))).one()
    checks = list((await db.scalars(select(HealthCheck).where(HealthCheck.service_id == service.id, HealthCheck.checked_at >= from_time, HealthCheck.checked_at <= to_time).order_by(HealthCheck.checked_at.desc()).limit(1000))).all())
    durations = sorted([check.response_ms for check in checks if check.response_ms is not None])
    percentile = durations[min(len(durations) - 1, round(0.95 * (len(durations) - 1)))] if durations else None
    total_checks, successful_checks, average_response_ms, min_response_ms, max_response_ms = summary
    total_checks = total_checks or 0; successful_checks = successful_checks or 0
    return ServiceAnalytics(from_time=from_time, to_time=to_time, total_checks=total_checks, successful_checks=successful_checks, failed_checks=total_checks - successful_checks, uptime_percent=round(successful_checks / total_checks * 100, 2) if total_checks else None, average_response_ms=round(average_response_ms, 2) if average_response_ms is not None else None, min_response_ms=min_response_ms, max_response_ms=max_response_ms, p95_response_ms=percentile, checks=checks[:200])

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
