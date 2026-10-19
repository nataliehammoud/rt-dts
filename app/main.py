from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import Base, engine
from app.api.tasks import router as tasks_router
from app.api.scheduler import router as scheduler_router
from app.ws.routes import router as ws_router
from app.ws.bridge import start_bridge, stop_bridge

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting RT-DTS API...")
    await start_bridge()
    yield
    # Shutdown
    print("🛑 Shutting down RT-DTS API...")
    await stop_bridge()


app = FastAPI(
    title="RT-DTS API",
    version="0.3.0",
    lifespan=lifespan,
)

app.include_router(tasks_router)
app.include_router(scheduler_router)
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok"}