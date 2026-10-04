import axios from 'axios';

// Head Office agent service. Outside docker-compose it runs on :8001
// (compose maps 8001 -> container 8000).
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000, // LLM tool-calling rounds can take a while
});

export interface WarehouseState {
  status: string;
  orders: number;
  workers: number;
  workers_required: number;
  capacity_utilization: number;
  risk_score: number;
  predicted_workload: string | number;
}

export interface NetworkStateResponse {
  warehouses: Record<string, WarehouseState>;
  total_warehouses: number;
  overall_health: 'GOOD' | 'ATTENTION' | 'CRITICAL' | 'NO_DATA';
  average_risk: number;
  worker_shortages: number;
  active_alerts: number;
  pending_decisions: number;
}

export interface ActiveEvent {
  warehouse_id: string;
  type: string;
  severity: 'HIGH' | 'MEDIUM' | string;
}

export interface Decision {
  decision_id: string | null;
  timestamp: string;
  event: string;
  warehouse: string;
  tools_called: string[];
  recommendation: string;
  reasoning: string[];
  status: string;
  resolved_at?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  toolsUsed?: string[];
}

export default api;
