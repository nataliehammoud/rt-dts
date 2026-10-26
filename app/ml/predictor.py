"""
Duration Predictor
==================
يتوقع مدة تنفيذ المهمة بناءً على الخصائص.
Linear Regression — بسيط وسريع.
"""
import joblib
from pathlib import Path

from sklearn.linear_model import LinearRegression

from app.db.session import SessionLocal
from app.db.models import Task, TaskStatus


MODEL_PATH = Path(__file__).parent / "duration_model.joblib"
_model_cache = {"model": None}


def _train() -> bool:
    """يدرب الموديل على المهام المكتملة. يرجع True إذا نجح."""
    db = SessionLocal()
    try:
        tasks = (
            db.query(Task)
            .filter(Task.status == TaskStatus.completed.value)
            .filter(Task.started_at.isnot(None))
            .filter(Task.finished_at.isnot(None))
            .all()
        )

        if len(tasks) < 5:
            return False

        X = [[t.duration, t.period or 0.0] for t in tasks]
        y = [(t.finished_at - t.started_at).total_seconds() for t in tasks]

        model = LinearRegression()
        model.fit(X, y)
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


def predict_duration(duration: float, period: float = 0.0) -> float:
    """يتوقع المدة بالثواني. يرجع duration كـ fallback لو ما في موديل."""
    model = _load_model()
    if model is None:
        return float(duration)

    prediction = model.predict([[duration, period]])
    return max(0.0, float(prediction[0]))


def retrain() -> bool:
    """يعيد تدريب الموديل. يرجع True إذا نجح."""
    _model_cache["model"] = None
    return _train()