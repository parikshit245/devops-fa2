import asyncio
from contextlib import suppress
from datetime import datetime, timezone
import httpx
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.service import MonitoredService
from app.monitoring.checker import run_check

class MonitoringScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._in_flight: set[str] = set()

    async def start(self) -> None:
        if self._task and not self._task.done(): return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="pulseops-monitoring")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError): await self._task
            self._task = None

    async def _run(self) -> None:
        async with httpx.AsyncClient() as client:
            while self._running:
                try:
                    async with SessionLocal() as db:
                        services = list((await db.scalars(select(MonitoredService).where(MonitoredService.monitoring_enabled))).all())
                    await asyncio.gather(*(self._check_if_due(service.id, client) for service in services), return_exceptions=True)
                except Exception:
                    pass
                await asyncio.sleep(5)

    async def _check_if_due(self, service_id, client: httpx.AsyncClient) -> None:
        key = str(service_id)
        if key in self._in_flight: return
        async with SessionLocal() as db:
            service = await db.get(MonitoredService, service_id)
            if not service or not service.monitoring_enabled: return
            last_check = service.last_check_at
            if last_check and last_check.tzinfo is None:
                last_check = last_check.replace(tzinfo=timezone.utc)
            if last_check and (datetime.now(timezone.utc) - last_check).total_seconds() < service.check_interval_seconds:
                return
            self._in_flight.add(key)
            try: await run_check(service, db, client)
            finally: self._in_flight.discard(key)

scheduler = MonitoringScheduler()
