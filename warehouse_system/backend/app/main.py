from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.api import auth, ml, agent, notifications, workload, head_office, approvals, ps_demo, inbound, outbound
import logging

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Warehouse Operations System API")

import asyncio
from app.db.database import SessionLocal
from app.services.head_office_sync import sync_warehouse_status_to_head_office

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

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_head_office_sync())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

@app.get("/health")
def health_check():
    return {"status": "ok"}
