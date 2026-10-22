"""
Data Warehouse Models (Star Schema)
====================================
جداول التحليل (OLAP) — منفصلة عن جداول التشغيل (OLTP)

Star Schema:
- fact_task_execution: الحقيقة الرئيسية
- dim_task: أبعاد المهمة
- dim_worker: أبعاد الـ Worker
- dim_time: أبعاد الوقت
- dim_status: أبعاد الحالة
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


# ============================================================
# Dimensions (الأبعاد)
# ============================================================

class DimTask(Base):
    """بُعد المهمة — معلومات ثابتة عن المهام"""
    __tablename__ = "dim_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    duration = Column(Float, nullable=False)
    period = Column(Float, nullable=True)
    deadline = Column(Float, nullable=True)


class DimWorker(Base):
    """بُعد الـ Worker"""
    __tablename__ = "dim_worker"

    id = Column(Integer, primary_key=True, autoincrement=True)
    worker_id = Column(String(100), nullable=False, unique=True, index=True)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)


class DimStatus(Base):
    """بُعد الحالة"""
    __tablename__ = "dim_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)


class DimTime(Base):
    """بُعد الوقت — لتحليل حسب الوقت"""
    __tablename__ = "dim_time"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_date = Column(DateTime, nullable=False, unique=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    hour = Column(Integer, nullable=False)
    minute = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday
    is_weekend = Column(Integer, nullable=False)   # 0 أو 1


# ============================================================
# Fact Table (الحقيقة)
# ============================================================

class FactTaskExecution(Base):
    """
    جدول الحقائق الرئيسي — كل تنفيذ مهمة = صف هنا.
    
    Foreign Keys للـ dimensions + metrics (قابلة للقياس)
    """
    __tablename__ = "fact_task_execution"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign Keys
    task_id = Column(Integer, ForeignKey("dim_task.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("dim_worker.id"), nullable=False, index=True)
    status_id = Column(Integer, ForeignKey("dim_status.id"), nullable=False, index=True)
    time_id = Column(Integer, ForeignKey("dim_time.id"), nullable=False, index=True)

    # Metrics
    wait_time = Column(Float, nullable=True)       # وقت الانتظار (ثواني)
    execution_time = Column(Float, nullable=True)  # وقت التنفيذ
    total_time = Column(Float, nullable=True)      # الكلي
    attempts = Column(Integer, default=1)          # عدد المحاولات
    deadline_met = Column(Integer, default=1)      # 1 = نعم، 0 = لا

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())

    # Relationships (للـ queries السهلة)
    task = relationship("DimTask")
    worker = relationship("DimWorker")
    status = relationship("DimStatus")
    time = relationship("DimTime")


# ============================================================
# Indexes للأداء
# ============================================================

# Composite index للتحليلات الشائعة
Index("idx_fact_task_worker", FactTaskExecution.task_id, FactTaskExecution.worker_id)
Index("idx_fact_time_status", FactTaskExecution.time_id, FactTaskExecution.status_id)