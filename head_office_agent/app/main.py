import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

from state.repository import InMemoryNetworkStateRepository
from state.manager import StateManager
from events.handler import EventHandler
from audit.logger import AuditLogger
from tools.simulation_tools import SimulationTools
from tools.resource_tools import ResourceTools
from decisions.engine import DecisionEngine
from providers.llm import NvidiaLLMProvider
from providers.optimization import MockOptimizationProvider
from communication.mock_adapter import MockCommunicationAdapter
from api.routes import router, init_routes
from api.auth import auth_router

load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Head Office Agent", description="Central intelligence orchestrator for warehouse network")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency initialization
repo = InMemoryNetworkStateRepository()
state_manager = StateManager(repo)
audit_logger = AuditLogger()
simulation_tools = SimulationTools(state_manager)
resource_tools = ResourceTools(state_manager)
decision_engine = DecisionEngine(state_manager, resource_tools)
event_handler = EventHandler(state_manager, decision_engine, audit_logger)
llm_provider = NvidiaLLMProvider()
comm_adapter = MockCommunicationAdapter()
optimizer = MockOptimizationProvider()

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

app.include_router(auth_router, prefix="/api")
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
