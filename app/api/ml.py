"""
ML API
======
نقاط النهاية للذكاء الاصطناعي.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ml import predictor, anomaly


router = APIRouter(prefix="/ml", tags=["AI"])


class DurationInput(BaseModel):
    duration: float = Field(..., gt=0, description="مدة المهمة بالثواني")
    period: float = Field(0.0, ge=0, description="فترة المهمة (اختياري)")


class AnomalyInput(BaseModel):
    total_tasks: int = Field(..., ge=0)
    failed_tasks: int = Field(..., ge=0)
    avg_duration: float = Field(..., ge=0)


@router.post("/predict-duration")
def predict_duration_endpoint(input: DurationInput):
    """يتوقع المدة الفعلية للتنفيذ."""
    predicted = predictor.predict_duration(input.duration, input.period)
    return {
        "input": input.model_dump(),
        "predicted_duration_seconds": round(predicted, 2),
    }


@router.post("/detect-anomaly")
def detect_anomaly_endpoint(input: AnomalyInput):
    """يحدد إذا كان worker شاذ."""
    is_anomaly = anomaly.detect_anomaly(
        input.total_tasks, input.failed_tasks, input.avg_duration
    )
    return {
        "input": input.model_dump(),
        "is_anomaly": is_anomaly,
        "message": "Worker looks unusual" if is_anomaly else "Worker looks normal",
    }


@router.post("/train-models")
def train_models_endpoint():
    """يعيد تدريب الموديلين على أحدث البيانات."""
    duration_ok = predictor.retrain()
    anomaly_ok = anomaly.retrain()
    return {
        "duration_model_trained": duration_ok,
        "anomaly_model_trained": anomaly_ok,
        "note": "Not enough data" if not (duration_ok and anomaly_ok) else "OK",
    }


@router.get("/model-stats")
def model_stats():
    """حالة الموديلات."""
    return {
        "duration_model_exists": predictor.MODEL_PATH.exists(),
        "anomaly_model_exists": anomaly.MODEL_PATH.exists(),
    }