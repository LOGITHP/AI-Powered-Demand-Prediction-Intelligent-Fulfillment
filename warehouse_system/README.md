# AI-Assisted Warehouse Management System

An intelligent, multi-agent warehouse orchestration platform that combines **Predictive Machine Learning**, **Autonomous AI Agents (LangGraph)**, and **Real-Time Interactive Dashboards** to optimize supply chain operations.

---

## 🏗 System Architecture & Flow

The system operates across three interconnected layers:

1. **Frontend Layer (React + Vite + TailwindCSS)**: 
   - **Manager Dashboard**: Provides a high-level view of warehouse operations. Displays live Machine Learning inferences (e.g., Delay Risk, Labour Requirements) and provides a conversational chat interface to the AI Orchestration Agent. Managers can also download real-time CSV reports.
   - **Operations Worker Dashboard**: An interface tailored for warehouse staff on the floor. It receives tasks directly from the dynamic Workload Queue and pushes operational events (e.g., Task Completions) back to the backend.

2. **Backend Services & AI Layer (FastAPI + LangGraph + Python ML)**:
   - Built on **FastAPI**, this layer securely handles all HTTP requests with JWT Authentication.
   - **LangGraph AI Orchestrator**: An autonomous agent that constantly monitors the warehouse state, communicates with Head Office simulations, and executes dynamic re-allocations.
   - **Machine Learning Inference**: Pre-trained deterministic models (XGBoost & Logistic Regression) are serialized into `.pkl` format. FastAPI loads these models into memory and serves live probability endpoints (e.g., `/api/ml/delay/predict`).

3. **Data Layer (PostgreSQL + Redis)**:
   - **PostgreSQL**: Stores persistent state such as User Accounts, Workload Queues, Tasks, and an Audit Log of Agent actions.
   - **Redis**: Functions as a fast, in-memory cache/broker for transient state and LangGraph memory persistence.

---

## 🛠 Technology Stack

- **Frontend**: React 18, Vite, TypeScript, TailwindCSS v3, Lucide React (Icons)
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Uvicorn, LangGraph, LangChain, Pydantic
- **Machine Learning**: Scikit-Learn, XGBoost, Pandas, Numpy
- **Database**: PostgreSQL (Persistent storage), Redis (Session state & memory)
- **Deployment**: Docker, Docker Compose

---

## 🚀 Key Features

### 1. Autonomous AI Agent (LangGraph)
The core of the system is the intelligent agent loop. When a manager submits a query through the UI, the LLM determines the optimal tool to invoke:
- `fetch_warehouse_state`: Pulls real-time backlog sizes and worker counts from the DB.
- `calculate_labour`: Triggers the deterministic XGBoost model for exact mathematical requirements.
- `escalate_to_manager`: Pauses the graph execution, sending an actionable prompt to the Manager Dashboard requiring human intervention before continuing.
- `assign_workers`: Automatically mutates the database to move workers between zones (e.g., Packing to Picking) to clear bottlenecks.

### 2. Predictive ML Pipeline
Data is generated and modeled across 4 factors:
1. **Delay Risk** (`LogisticRegression`): 95% F1-score prediction on SLA breaches.
2. **Labour Requirements** (`XGBoost`): Regresses exactly how many workers are needed given SKU complexity and historical volume.
3. **Processing Time** (`RandomForestRegressor`): Predicts task duration based on worker skill-level and distance vectors.
4. **Congestion Risk** (`LogisticRegression`): Detects physical path bottlenecks.

### 3. Worker-to-Agent Interactive Feedback
Workers are not just blind executors. If the AI Agent dynamically reassigns a worker to a new zone, the worker receives an immediate actionable notification on their terminal. They can acknowledge the assignment or send a reply back to the system, feeding the LangGraph memory buffer with ground-truth updates.

---

## 🗄 Database Design

The PostgreSQL database (powered by SQLAlchemy) manages the following key entities:
- `users`: Core authentication definitions across roles (MANAGER, INBOUND, OUTBOUND, WORKER).
- `workers`: Extensions of the user profile capturing `skill_level`, `experience_years`, and `assigned_zone`.
- `workload_queues`: Aggregated volume metrics for each operational process (e.g., RECEIVING, PICKING).
- `tasks`: Granular, step-by-step job assignments consumed by the Operations Frontend.
- `notifications`: Two-way messaging backbone between the LangGraph agent and human staff.
- `agent_actions`: Immutable audit log tracking every tool invoked by the LLM.

---

## ⚙️ Running Locally

The entire system is completely containerized and can be launched with a single command:

```bash
docker-compose up --build -d
```

### Access Points
- **Manager Dashboard**: `http://localhost:3000` (Login: `manager` / `manager123`)
- **Operations Worker**: `http://localhost:3001` (Login: `worker001` / `password`)
- **Backend API Docs (Swagger UI)**: `http://localhost:8000/docs`

> *Note: For the AI Agent to function, ensure `NVIDIA_API_KEY` is provided in the backend `.env`.*

---

## 🎯 PS Requirements Demonstration

The system has been specifically architected to visibly demonstrate the PS (Problem Statement) requirements on the frontend. The Manager Dashboard contains 5 dedicated pages populated with deterministic seed data from the backend to ensure consistent evaluation:

1. **/forecasting (Volume Forecasting)**: Demonstrates Inbound Shipment forecasts, Outbound Order predictions, Inventory Movement trends, and Workload Projections using Recharts visualizations.
2. **/workforce (Smart Workforce Planning)**: Showcases ML-predicted labour requirements, recommended staffing levels, shift planning tables, and dynamic resource vs. forecasted demand charts.
3. **/analytics (Operations Efficiency)**: Provides operational KPIs against industry benchmarks, receiving/picking throughput and cycle times, storage utilization, and AI-generated insights for bottlenecks.
4. **/optimization (Resource Optimization Engine)**: Highlights underutilized and overutilized areas, provides actionable workforce redistribution recommendations, visualizes labour planning accuracy, and features a functional Peak/Non-Peak Scenario Simulator.
5. **/ps-requirements (Coverage Checklist)**: A dedicated directory directly mapping the PS goals to their functional implementation pages.
