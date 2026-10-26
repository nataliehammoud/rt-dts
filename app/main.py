from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.core.redis_client import redis_client
from app.db.session import Base, engine
from app.api.tasks import router as tasks_router
from app.api.scheduler import router as scheduler_router
from app.api.analytics import router as analytics_router
from app.api.ml import router as ml_router
from app.ws.routes import router as ws_router
from app.ws.bridge import start_bridge, stop_bridge
from app.warehouse.etl import etl_worker
from app.workers.cleanup import cleanup_worker
from app.core.logging import setup_logging, get_logger

logger = get_logger(__name__)

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("INFO")
    logger.info("api_starting")
    await start_bridge()
    etl_task = asyncio.create_task(etl_worker(redis_client, interval_seconds=30))
    cleanup_task = asyncio.create_task(cleanup_worker(interval_seconds=60))
    yield
    logger.info("api_stopping")
    etl_task.cancel()
    cleanup_task.cancel()
    for t in (etl_task, cleanup_task):
        try:
            await t
        except asyncio.CancelledError:
            pass
    await stop_bridge()


app = FastAPI(
    title="RT-DTS API",
    version="0.4.0",
    lifespan=lifespan,
)

app.include_router(tasks_router)
app.include_router(scheduler_router)
app.include_router(analytics_router)
app.include_router(ml_router)
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def dashboard():
    return FileResponse("app/static/index.html")