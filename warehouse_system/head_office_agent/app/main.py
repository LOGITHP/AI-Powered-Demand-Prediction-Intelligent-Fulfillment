import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.core import engine, Base
from dotenv import load_dotenv

from state.repository import InMemoryNetworkStateRepository
from state.manager import StateManager
from events.handler import EventHandler
from audit.logger import AuditLogger
from tools.simulation_tools import SimulationTools
from providers.llm import NvidiaLLMProvider
from providers.optimization import RealOptimizationProvider
from communication.mock_adapter import MockCommunicationAdapter
from api.routes import router as ai_router, init_routes

# Import API routes
from api.v1 import agents, orders, warehouses, inventory

load_dotenv()

app = FastAPI(title="Head Office System", version="1.0.0")

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

from tools.resource_tools import ResourceTools
from decisions.engine import DecisionEngine

# Dependency initialization for AI Agent
repo = InMemoryNetworkStateRepository()
state_manager = StateManager(repo)
audit_logger = AuditLogger()
resource_tools = ResourceTools(state_manager)
decision_engine = DecisionEngine(state_manager, resource_tools)
event_handler = EventHandler(state_manager, decision_engine, audit_logger)
simulation_tools = SimulationTools(state_manager)
llm_provider = NvidiaLLMProvider()
comm_adapter = MockCommunicationAdapter()
optimizer = RealOptimizationProvider()

# Initialize API routes with dependencies
init_routes(
    sm=state_manager,
    eh=event_handler,
    al=audit_logger,
    st=simulation_tools,
    llm=llm_provider,
    ca=comm_adapter,
    optimizer=optimizer
)

# Include AI Router
app.include_router(ai_router)

# Include CRUD Routers
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(warehouses.router, prefix="/api/v1/warehouses", tags=["Warehouses"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])

@app.on_event("startup")
def startup_event():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
