# AI-Powered Demand Prediction & Intelligent Fulfillment

An intelligent, multi-agent warehouse orchestration platform that combines **Predictive Machine Learning**, **Autonomous AI Agents (LangGraph)**, and **Real-Time Interactive Dashboards** to optimize supply chain operations.

## 📁 Repository Structure

This repository is divided into two main components:

1. **`warehouse_system/`**: The core application containing the frontend dashboards, backend APIs, and the LangGraph AI Orchestrator.
2. **`warehouse_ml/`**: The Machine Learning pipeline for training predictive models (Delay Risk, Labour Requirements, Processing Time, Congestion Risk).

---

## 🏗 System Architecture

The system operates across three interconnected layers:

1. **Frontend Layer (React + Vite + TailwindCSS)**: 
   - **Manager Dashboard**: High-level view of warehouse operations. Displays live ML inferences and provides a conversational chat interface to the AI Orchestration Agent.
   - **Operations Worker Dashboard**: An interface tailored for warehouse staff on the floor. It receives tasks directly from the dynamic Workload Queue.
   - **Inbound/Outbound/Head Office**: Specialized frontends for different parts of the fulfillment lifecycle.

2. **Backend Services & AI Layer (FastAPI + LangGraph + Python ML)**:
   - **FastAPI**: Handles HTTP requests, JWT Authentication, and serves ML models.
   - **LangGraph AI Orchestrator**: An autonomous agent that monitors the warehouse state and executes dynamic re-allocations.
   - **Machine Learning Inference**: Pre-trained deterministic models (XGBoost & Logistic Regression) serialized into `.pkl` format for live probability endpoints.

3. **Data Layer (PostgreSQL + Redis)**:
   - **PostgreSQL**: Stores persistent state (User Accounts, Workload Queues, Tasks, Audit Logs).
   - **Redis**: Fast, in-memory cache for transient state and LangGraph memory persistence.

---

## 🚀 Key Features

- **Autonomous AI Agent (LangGraph)**: Constant monitoring, automatic worker reassignment, and bottleneck resolution.
- **Predictive ML Pipeline**: Forecasting delay risk, labour requirements, processing time, and congestion risk.
- **Interactive Feedback**: Two-way communication between the AI agent and human workers on the floor.
- **Real-Time Dashboards**: Manager and worker dashboards for tracking volume, operations, and AI actions.

---

## 🛠 Technology Stack

- **Frontend**: React 18, Vite, TypeScript, TailwindCSS v3, Lucide React
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Uvicorn, LangGraph, LangChain, Pydantic
- **Machine Learning**: Scikit-Learn, XGBoost, Pandas, Numpy
- **Database**: PostgreSQL, Redis
- **Deployment**: Docker, Docker Compose

---

## ⚙️ Running the Project Locally

### 1. Launch the Warehouse System (Core App)

The entire application stack (Frontend, Backend, DBs) is containerized using Docker Compose.

```bash
cd warehouse_system
docker-compose up --build -d
```

#### Access Points:
- **Manager Dashboard**: `http://localhost:3000` (Login: `manager` / `manager123`)
- **Operations Worker Dashboard**: `http://localhost:3001` (Login: `worker001` / `password`)
- **Backend API Docs (Swagger UI)**: `http://localhost:8000/docs`

> *Note: For the AI Agent to function, ensure `NVIDIA_API_KEY` is provided in the `warehouse_system/backend/.env` file.*

### 2. Machine Learning Pipeline (Optional)

If you want to re-train the models or explore the data generation process:

```bash
cd warehouse_ml
pip install -r requirements.txt

# Generate synthetic data
python src/generate_data.py

# Train models
python src/train_labour.py
python src/train_processing.py
python src/train_delay.py
python src/train_congestion.py
```

For more details on the ML pipeline, refer to the [Machine Learning README](warehouse_ml/README.md).
For more details on the System Architecture, refer to the [Warehouse System README](warehouse_system/README.md).
