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

load_dotenv()

app = FastAPI(title="Head Office Agent", description="Central intelligence orchestrator for warehouse network")

# Dependency initialization
repo = InMemoryNetworkStateRepository()
state_manager = StateManager(repo)
resource_tools = ResourceTools(state_manager)
decision_engine = DecisionEngine(state_manager, resource_tools)
audit_logger = AuditLogger()
event_handler = EventHandler(state_manager, decision_engine, audit_logger)
simulation_tools = SimulationTools(state_manager)
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

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
