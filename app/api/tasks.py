from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.db.session import get_db
from app.db.models import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])

class TaskCreate(BaseModel):
    name: str
    duration: float
    period: Optional[float] = None
    deadline: Optional[float] = None

class TaskOut(BaseModel):
    id: int
    name: str
    duration: float
    period: Optional[float]
    deadline: Optional[float]
    status: str

    class Config:
        from_attributes = True

@router.post("/", response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.get("/", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.id.desc()).all()

@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task