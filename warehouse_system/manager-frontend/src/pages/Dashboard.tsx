import { useState, useEffect } from 'react';
import { Users, Package, AlertTriangle } from 'lucide-react';
import api from '../lib/api';

export default function Dashboard() {
  const [delayRisk, setDelayRisk] = useState<number | null>(null);
  const [activeTasks, setActiveTasks] = useState<number>(0);
  const [assignedWorkers, setAssignedWorkers] = useState<number>(0);
  const [totalPresent, setTotalPresent] = useState<number>(50);

  // No chat history needed here
  const fetchLiveMetrics = async () => {
    try {
      const mlData = {
        warehouse_id: 'WH01',
        shift: 1,
        process_type: 'PICKING',
        workload_quantity: 1204, // To be overridden
        number_of_orders: 150,
        number_of_items: 2000,
        number_of_skus: 500,
        scheduled_workers: 50,
        available_workers: 42,
        average_worker_experience: 2.5,
        average_worker_skill: 3.8,
        equipment_available: 0.9,
        current_queue: 1204,
        warehouse_utilization: 0.85,
        historical_productivity: 1.2,
        distance_factor: 1.5,
        task_complexity: 2.0
      };
      
      try {
        const [inRes, outRes, wfRes] = await Promise.all([
          api.get('/inbound/kpis'),
          api.get('/outbound/kpis'),
          api.get('/ps/workforce')
        ]);
        const inbound = inRes.data;
        const outbound = outRes.data;
        const workforce = wfRes.data;

        const activeTasksCount = outbound.in_queue + inbound.in_queue;
        const assignedCount = (inbound.workforce.receiving.assigned + 
                                 inbound.workforce.inspection.assigned + 
                                 inbound.workforce.putaway.assigned + 
                                 outbound.workforce.picking.assigned + 
                                 outbound.workforce.packing.assigned + 
                                 outbound.workforce.loading.assigned);
        
        mlData.workload_quantity = activeTasksCount > 0 ? activeTasksCount : 10;
        mlData.number_of_orders = outbound.in_queue > 0 ? outbound.in_queue : 5;
        mlData.current_queue = activeTasksCount > 0 ? activeTasksCount : 10;
        if (assignedCount > 0) mlData.available_workers = assignedCount;
        
        setActiveTasks(activeTasksCount);
        setAssignedWorkers(assignedCount);
        setTotalPresent(workforce.manpower?.available || 50);
      } catch (e) {
        console.error("Could not fetch KPIs", e);
      }
      
      const res = await api.post('/ml/delay/predict', mlData);
      // The API returns { probability: float, status: string }
      setDelayRisk(Math.round(res.data.probability * 100));
    } catch (err) {
      console.error("Failed to fetch ML metrics", err);
    }
  };

  useEffect(() => {
    fetchLiveMetrics();
  }, []);

  // No agent logic needed here
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <header className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Operations Dashboard</h1>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => {
              const csvContent = "data:text/csv;charset=utf-8,Metric,Value\nWorkforce Availability,42\nActive Tasks,1204\nDelay Risk Probability," + (delayRisk ?? "Loading") + "%\n";
              const encodedUri = encodeURI(csvContent);
              const link = document.createElement("a");
              link.setAttribute("href", encodedUri);
              link.setAttribute("download", "warehouse_report.csv");
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Download Report
          </button>
          <span className="flex items-center gap-2 bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-sm font-medium">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            System Healthy
          </span>
        </div>
      </header>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-gray-200 flex items-start justify-between shadow-sm hover:border-gray-300 transition-colors">
          <div>
            <p className="text-gray-500 text-sm font-medium">Workforce Availability</p>
            <p className="text-3xl font-bold mt-2">{assignedWorkers || 0} <span className="text-sm text-gray-400 font-normal">/ {totalPresent} Present</span></p>
          </div>
          <div className="p-3 bg-blue-500/20 rounded-xl text-blue-400">
            <Users size={24} />
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-2xl border border-gray-200 flex items-start justify-between shadow-sm hover:border-gray-300 transition-colors">
          <div>
            <p className="text-gray-500 text-sm font-medium">Active Tasks</p>
            <p className="text-3xl font-bold mt-2">{activeTasks || 0} <span className="text-sm text-gray-400 font-normal">Pending</span></p>
          </div>
          <div className="p-3 bg-purple-500/20 rounded-xl text-purple-400">
            <Package size={24} />
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-2xl border border-gray-200 flex items-start justify-between shadow-sm hover:border-gray-300 transition-colors">
          <div>
            <p className="text-gray-500 text-sm font-medium">ML Delay Risk</p>
            <p className={`text-3xl font-bold mt-2 ${delayRisk !== null && delayRisk > 50 ? 'text-red-400' : 'text-yellow-400'}`}>
              {delayRisk !== null ? `${delayRisk}%` : 'Loading...'} <span className="text-sm text-gray-400 font-normal text-gray-500">Probability</span>
            </p>
          </div>
          <div className={`p-3 rounded-xl ${delayRisk !== null && delayRisk > 50 ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
            <AlertTriangle size={24} />
          </div>
        </div>
      </div>

      {/* Business Goals / Core System Capabilities */}
      <div className="mt-8 space-y-4">
        <h2 className="text-2xl font-bold text-gray-900">System Capabilities</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="font-bold text-blue-800 mb-2">1. Volume Forecasting</h3>
            <ul className="text-sm text-gray-600 space-y-1 list-disc pl-4">
              <li>Predict inbound shipment volumes</li>
              <li>Forecast outbound order volumes</li>
              <li>Estimate inventory movement trends</li>
              <li>Provide workload projections based on data</li>
            </ul>
          </div>
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="font-bold text-purple-800 mb-2">2. Workforce Planning</h3>
            <ul className="text-sm text-gray-600 space-y-1 list-disc pl-4">
              <li>Calculate manpower automatically</li>
              <li>Recommend optimal staffing levels</li>
              <li>Support shift planning & allocation</li>
              <li>Match resources against demand</li>
            </ul>
          </div>
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="font-bold text-green-800 mb-2">3. Efficiency Dashboard</h3>
            <ul className="text-sm text-gray-600 space-y-1 list-disc pl-4">
              <li>Establish operational KPIs</li>
              <li>Measure inbound & outbound efficiency</li>
              <li>Track throughput, cycle time, utilization</li>
              <li>Provide trend analysis & insights</li>
            </ul>
          </div>
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
            <h3 className="font-bold text-orange-800 mb-2">4. Resource Optimization</h3>
            <ul className="text-sm text-gray-600 space-y-1 list-disc pl-4">
              <li>Identify under/overutilized areas</li>
              <li>Recommend workforce redistribution</li>
              <li>Improve labor planning accuracy</li>
              <li>Support scenario-based planning</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
