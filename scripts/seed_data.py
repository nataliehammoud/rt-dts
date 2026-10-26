"""
Seed Data
=========
ينشئ 20 مهمة مكتملة في قاعدة البيانات (للاختبار ETL + Analytics).

Usage:
    python scripts/seed_data.py
"""
import asyncio
import sys
import os
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.db.models import Task, TaskStatus


TASK_NAMES = ["data_processing", "image_resize", "report_gen", "email_send", "db_backup"]


def seed():
    db = SessionLocal()

    try:
        count = 0
        for i in range(20):
            status = (
TaskStatus.completed.value
                if random.random() > 0.2
else TaskStatus.failed.value
            )

            task = Task(
                name=random.choice(TASK_NAMES),
                duration=round(random.uniform(0.5, 5.0), 2),
                period=random.choice([10.0, 15.0, 20.0]),
                deadline=random.choice([5.0, 8.0, 10.0]),
                status=status,
created_at=datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 120)),
            )
            db.add(task)
            count += 1

        db.commit()
        print(f"✅ Created {count} tasks (18 completed + 2 failed approx)")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()