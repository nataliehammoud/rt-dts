from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from app.db.session import Base
import enum

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    duration = Column(Float, nullable=False)
    period = Column(Float, nullable=True)
    deadline = Column(Float, nullable=True)
    status = Column(String(50), default=TaskStatus.PENDING.value)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)