"""
Anomaly Detector
================
يكشف workers اللي بيتصرفوا بشكل شاذ.
Isolation Forest — مناسب للبيانات الصغيرة.
"""
import joblib
from pathlib import Path

from sklearn.ensemble import IsolationForest
from sqlalchemy import func, case

from app.db.session import SessionLocal
from app.db.models import Task, TaskStatus


MODEL_PATH = Path(__file__).parent / "anomaly_model.joblib"
_model_cache = {"model": None}


def _train() -> bool:
    """يدرب الموديل على إحصائيات الـ workers. يرجع True إذا نجح."""
    db = SessionLocal()
    try:
        rows = (
            db.query(
                Task.worker_id,
                func.count(Task.id).label("total"),
                func.sum(case((Task.status == TaskStatus.failed.value, 1), else_=0)).label("failed"),
                func.avg(Task.duration).label("avg_duration"),
            )
            .filter(Task.worker_id.isnot(None))
            .group_by(Task.worker_id)
            .all()
        )

        if len(rows) < 3:
            return False

        X = [[r.total, r.failed or 0, r.avg_duration or 0.0] for r in rows]

        model = IsolationForest(contamination=0.2, random_state=42)
        model.fit(X)
        joblib.dump(model, MODEL_PATH)
        return True
    finally:
        db.close()


def _load_model():
    """يحمّل الموديل من الذاكرة أو الملف، أو يدرب إذا ما موجود."""
    if _model_cache["model"] is not None:
        return _model_cache["model"]

    if MODEL_PATH.exists():
        model = joblib.load(MODEL_PATH)
    else:
        _train()
        model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None

    _model_cache["model"] = model
    return model


def detect_anomaly(total_tasks: int, failed_tasks: int, avg_duration: float) -> bool:
    """يرجع True إذا كان worker شاذ."""
    # Business rules (بديهيات) — تطبق دائمًا
    if total_tasks > 0:
        failure_rate = failed_tasks / total_tasks
        if failure_rate >= 0.5:  # 50%+ فشل = شاذ
            return True

    if avg_duration > 100:  # أكثر من 100 ثانية = شاذ
        return True

    # ML model للحالات الدقيقة
    model = _load_model()
    if model is None:
        return False

    prediction = model.predict([[total_tasks, failed_tasks, avg_duration]])
    return int(prediction[0]) == -1


def retrain() -> bool:
    """يعيد تدريب الموديل. يرجع True إذا نجح."""
    _model_cache["model"] = None
    return _train()