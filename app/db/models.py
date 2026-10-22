from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class TaskStatus(enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    duration = Column(Float, nullable=False)
    period = Column(Float, nullable=True)
    deadline = Column(Float, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending)

    # ✅ تتبع worker
    worker_id = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)   # ← لازم تكون موجودة

    # timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())