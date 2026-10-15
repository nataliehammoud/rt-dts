from fastapi import FastAPI
from app.db.session import Base, engine
from app.api.tasks import router as tasks_router
from app.api.scheduler import router as scheduler_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RT-DTS API", version="0.2.0")

app.include_router(tasks_router)
app.include_router(scheduler_router)

@app.get("/health")
def health():
    return {"status": "ok"}