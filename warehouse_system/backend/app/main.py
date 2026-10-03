from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.api import auth, ml, agent
import logging

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Warehouse Operations System API")

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

@app.get("/health")
def health_check():
    return {"status": "ok"}
