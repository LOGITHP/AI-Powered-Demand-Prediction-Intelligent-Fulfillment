import { api, USE_MOCK } from './api';

export interface DashboardMetrics {
  ordersToday: number;
  pendingOrders: number;
  inboundShipments: number;
  outboundShipments: number;
  presentWorkers: number;
  requiredWorkers: number;
  utilizationPercent: number;
  delayedTasks: number;
}

const mockMetrics: DashboardMetrics = {
  ordersToday: 245,
  pendingOrders: 42,
  inboundShipments: 12,
  outboundShipments: 18,
  presentWorkers: 27,
  requiredWorkers: 32,
  utilizationPercent: 88,
  delayedTasks: 5
};

export const fetchDashboardMetrics = async (): Promise<DashboardMetrics> => {
  if (USE_MOCK) {
    return new Promise(resolve => setTimeout(() => resolve(mockMetrics), 500));
  }
  const response = await api.get('/api/dashboard/metrics');
  return response.data;
};
