from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.api import auth, ml, agent, notifications, workload, head_office, approvals, ps_demo, inbound, outbound, intelligence, connection_center
import logging

# Create DB tables
Base.metadata.create_all(bind=engine)

# Register Connection Center connectors (WMS, head office, LLM gateway)
from app.connection_center.bootstrap import init_default_connectors
init_default_connectors()

app = FastAPI(title="Warehouse Operations System API")

import asyncio
from app.db.database import SessionLocal
from app.services.head_office_sync import sync_warehouse_status_to_head_office
from app.services.notification_service import tick_escalations

async def background_head_office_sync():
    while True:
        try:
            db = SessionLocal()
            sync_warehouse_status_to_head_office(db, "WH-001")
        except Exception as e:
            logging.error(f"Error in background sync: {e}")
        finally:
            db.close()
        await asyncio.sleep(60) # Sync every 60 seconds

async def background_notification_escalation():
    """Escalation ladder for ack-required notifications (every 30s)."""
    while True:
        await asyncio.sleep(30)
        db = SessionLocal()
        try:
            tick_escalations(db)
        except Exception as e:
            logging.warning(f"Escalation tick failed: {e}")
        finally:
            db.close()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_head_office_sync())
    asyncio.create_task(background_notification_escalation())

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(ml.router, prefix="/api/ml", tags=["ml"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(workload.router, prefix="/api/workload", tags=["workload"])
app.include_router(head_office.router, prefix="/api/head-office", tags=["head_office"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(ps_demo.router, prefix="/api/ps", tags=["ps_demo"])
app.include_router(inbound.router, prefix="/api/inbound", tags=["inbound"])
app.include_router(outbound.router, prefix="/api/outbound", tags=["outbound"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["intelligence"])
app.include_router(connection_center.router, prefix="/api/connection-center", tags=["connection_center"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
