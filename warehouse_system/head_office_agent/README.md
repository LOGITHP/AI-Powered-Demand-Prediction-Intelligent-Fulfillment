# Head Office Agent

This repository contains the Head Office Agent for the multi-agent warehouse logistics system. 
It focuses ONLY on intelligence, orchestration, reasoning, tool-calling, coordination, and communication.

## Responsibilities
- Observes Warehouse Agents and maintains temporary in-memory network context.
- Identifies network-level problems (e.g. resource imbalance, bottlenecks).
- Decides which tools to call dynamically based on current scenarios.
- Generates transparent recommendations (pending approval) and acts via communication adapters.
- Provides APIs for frontends and dashboards to consume.

## Architecture
The system is fully modular and uses clean abstractions. 
It is structured into:
- **State Management** (`state/`): Manages the `NetworkState` and processes `WarehouseUpdate`s. Includes repository pattern for later DB integration.
- **Tools** (`tools/`): Executable tools the agent can use to query state, find resources, simulate actions.
- **Communication** (`communication/`): Adapters/Interfaces to talk to external Warehouse Agents (using a mock adapter for testing).
- **Decisions & Events** (`decisions/`, `events/`): Engine to reason about incoming events and draft decisions.
- **Providers** (`providers/`): External interfaces for ML models and LLMs, currently implemented as mocks.
- **API Layer** (`api/`): FastAPI endpoints for interacting with the agent.
- **Audit Logger** (`audit/`): Tracks decisions for human review.

## Dependencies
- `pydantic`
- `pytest`
- `fastapi`

## Running Tests
Run the end-to-end scenario test using `pytest`:

```bash
cd head_office_agent
set PYTHONPATH=.
pytest tests/test_scenario.py -v
```

This tests the exact requested scenario: 
- WH-A reports a worker shortage and high risk.
- WH-B reports a surplus.
- Head Office Agent detects this upon receiving the WORKER_SHORTAGE event.
- It finds the surplus in WH-B.
- It drafts a `WORKER_ALLOCATION` recommendation for 7 workers.
- The decision is logged and simulated as approved, firing a `RESOURCE_ALLOCATION_PROPOSAL` to the mock adapter.

## Integration
Other team members can plug their implementations directly into the interfaces provided in `providers/` and `communication/` or connect over the API routes in `api/routes.py`.
