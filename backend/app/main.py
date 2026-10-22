from contextlib import asynccontextmanager
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.api.routes import auth, health, resources
from app.core.config import get_settings
from app.metrics import http_request_duration_seconds, http_requests_in_progress, http_requests_total
from app.monitoring.scheduler import scheduler

settings = get_settings()
@asynccontextmanager
async def lifespan(_app: FastAPI):
    await scheduler.start()
    yield
    await scheduler.stop()

app = FastAPI(title="PulseOps API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router); app.include_router(auth.router); app.include_router(resources.router)

@app.middleware("http")
async def collect_http_metrics(request, call_next):
    started = time.perf_counter()
    status_code = 500
    http_requests_in_progress.inc()
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        http_requests_in_progress.dec()
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        if route_path != "/metrics":
            method = request.method
            http_requests_total.labels(method=method, route=route_path, status=str(status_code)).inc()
            http_request_duration_seconds.labels(method=method, route=route_path).observe(time.perf_counter() - started)

@app.get("/")
async def root() -> dict[str, str]: return {"name": "PulseOps API", "status": "ok"}
@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
