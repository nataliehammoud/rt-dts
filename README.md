# RT-DTS: Real-Time Distributed Task Scheduler

نظام جدولة مهام موزّع في الزمن الحقيقي مع خوارزميات RM و EDF.

## 🎯 الميزات

- **Scheduler**: خوارزميات Rate Monotonic (RM) و Earliest Deadline First (EDF) مكتوبة من الصفر
- **Schedulability Analysis**: LL Bound + Response Time Analysis (RTA)
- **REST API**: FastAPI مع Swagger UI
- **Database**: MySQL 8.0 مع SQLAlchemy
- **Message Broker**: Redis 7
- **Containerization**: Docker + Docker Compose

## 🏗️ المعمارية

```text
┌─────────────┐
│  React UI   │  ← (قريباً)
└──────┬──────┘
       │ WebSocket + REST
┌──────▼──────┐
│   FastAPI   │
└──┬───────┬──┘
   │       │
┌──▼──┐ ┌─▼────┐
│MySQL│ │Redis │
└─────┘ └──────┘

## 🚀 التشغيل

### المتطلبات
- Docker Desktop
- Docker Compose

### الخطوات

```bash
git clone https://github.com/nataliehammoud/rt-dts.git
cd rt-dts
docker compose up -d