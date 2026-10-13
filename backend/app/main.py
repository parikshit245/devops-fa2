from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.api.routes import auth, health, resources
from app.core.config import get_settings
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
@app.get("/")
async def root() -> dict[str, str]: return {"name": "PulseOps API", "status": "ok"}
@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
