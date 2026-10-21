import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["JWT_SECRET"] = "test-secret"

import pytest
import httpx
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.monitoring.ssrf import validate_public_url
from app.monitoring.checker import run_check
from app.models.service import MonitoredService
from app.models.user import User

engine = create_async_engine("sqlite+aiosqlite:///./test.db")
TestingSession = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def override_db():
    async with TestingSession() as session:
        yield session

app.dependency_overrides[get_db] = override_db

@pytest.fixture(autouse=True)
async def database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_health_and_registration():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).status_code == 200
        metrics = await client.get("/metrics")
        assert metrics.status_code == 200
        assert 'pulseops_http_requests_total{method="GET",route="/health",status="200"}' in metrics.text
        assert 'pulseops_http_request_duration_seconds_count{method="GET",route="/health"}' in metrics.text
        response = await client.post("/api/v1/auth/register", json={"name": "Maya", "email": "MAYA@example.com", "password": "correct horse battery"})
        assert response.status_code == 201
        assert response.json()["user"]["email"] == "maya@example.com"
        assert (await client.get("/api/v1/auth/me", cookies=response.cookies)).status_code == 200

@pytest.mark.asyncio
async def test_duplicate_and_unauthenticated_service_access():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"name": "Maya", "email": "maya@example.com", "password": "correct horse battery"}
        assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
        assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anonymous:
        assert (await anonymous.get("/api/v1/services")).status_code == 401

@pytest.mark.asyncio
async def test_service_crud_and_cross_user_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/auth/register", json={"name": "One", "email": "one@example.com", "password": "correct horse battery"})
        service = await client.post("/api/v1/services", json={"name": "API", "endpoint_url": "https://api.example.com", "environment": "production"})
        assert service.status_code == 201
        service_id = service.json()["id"]
        analytics = await client.get(f"/api/v1/services/{service_id}/analytics?days=30")
        assert analytics.status_code == 200
        assert analytics.json()["total_checks"] == 0
        assert analytics.json()["uptime_percent"] is None
        await client.post("/api/v1/auth/logout")
        await client.post("/api/v1/auth/register", json={"name": "Two", "email": "two@example.com", "password": "correct horse battery"})
        assert (await client.get(f"/api/v1/services/{service_id}")).status_code == 404
        assert (await client.patch(f"/api/v1/services/{service_id}", json={"name": "Nope"})).status_code == 404

@pytest.mark.asyncio
async def test_ssrf_rejects_private_destinations():
    with pytest.raises(Exception):
        await validate_public_url("http://127.0.0.1:8000")

@pytest.mark.asyncio
async def test_failed_checks_create_once_and_recovery_resolves():
    async with TestingSession() as session:
        user = User(name="Monitor", email="monitor@example.com", password_hash="not-used")
        session.add(user); await session.flush()
        service = MonitoredService(owner_id=user.id, name="Demo", endpoint_url="https://example.com")
        session.add(service); await session.commit(); await session.refresh(service)
        transport = httpx.MockTransport(lambda request: httpx.Response(503))
        async with httpx.AsyncClient(transport=transport) as client:
            await run_check(service, session, client)
            await run_check(service, session, client)
        assert service.status.value == "down"
        transport = httpx.MockTransport(lambda request: httpx.Response(200))
        async with httpx.AsyncClient(transport=transport) as client:
            await run_check(service, session, client)
        assert service.status.value == "operational"
