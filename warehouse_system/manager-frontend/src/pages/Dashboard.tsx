import { useState, useEffect } from 'react';
import { BrainCircuit, Send, Loader2, Users, Package, AlertTriangle, User } from 'lucide-react';
import api from '../lib/api';

interface Message {
  role: 'user' | 'agent';
  content: string;
}

export default function Dashboard() {
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState<Message[]>(() => {
    const saved = localStorage.getItem('agentChatHistory');
    return saved ? JSON.parse(saved) : [];
  });
  const [loading, setLoading] = useState(false);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [delayRisk, setDelayRisk] = useState<number | null>(null);
  const [activeTasks, setActiveTasks] = useState<number>(0);
  const [assignedWorkers, setAssignedWorkers] = useState<number>(0);

  useEffect(() => {
    localStorage.setItem('agentChatHistory', JSON.stringify(chatHistory));
  }, [chatHistory]);

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
        const [inRes, outRes] = await Promise.all([
          api.get('/inbound/kpis'),
          api.get('/outbound/kpis')
        ]);
        const inbound = inRes.data;
        const outbound = outRes.data;
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

  const fetchApprovals = async () => {
    try {
      const res = await api.get('/approvals');
      setApprovals(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleApproval = async (id: number, status: string) => {
    try {
      await api.put(`/approvals/${id}`, { status });
      fetchApprovals();
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchApprovals();
    fetchLiveMetrics();
  }, []);

  const askAgent = async () => {
    if (!query.trim()) return;
    
    const userMessage = query;
    setChatHistory(prev => [...prev, { role: 'user', content: userMessage }]);
    setQuery('');
    setLoading(true);
    
    try {
      const res = await api.post('/agent/chat', {
        message: userMessage,
        warehouse_id: 'WH01'
      });
      setChatHistory(prev => [...prev, { role: 'agent', content: res.data.response }]);
    } catch (err: any) {
      setChatHistory(prev => [...prev, { role: 'agent', content: "Error communicating with AI Agent. Is NVIDIA API Key configured?" }]);
    }
    setLoading(false);
  };

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
            <p className="text-3xl font-bold mt-2">{assignedWorkers || 0} <span className="text-sm text-gray-400 font-normal">/ 50 Present</span></p>
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

      {approvals.length > 0 && (
        <div className="bg-white rounded-2xl border border-yellow-500/30 overflow-hidden shadow-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="text-yellow-500" />
            <h2 className="text-xl font-bold text-gray-900">Pending Approvals Required</h2>
          </div>
          <div className="space-y-4">
            {approvals.map(approval => (
              <div key={approval.id} className="bg-gray-50 border border-gray-200 p-4 rounded-xl flex items-center justify-between">
                <div>
                  <p className="text-sm font-bold text-gray-700">Action: {approval.tool_called || "Worker Redistribution"}</p>
                  <p className="text-gray-500 text-sm mt-1">{approval.recommendation}</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleApproval(approval.id, 'REJECTED')} className="px-4 py-2 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg text-sm font-medium transition-colors">Reject</button>
                  <button onClick={() => handleApproval(approval.id, 'APPROVED')} className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors">Approve Action</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* LangGraph Agent Chat Interface */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-lg flex flex-col" style={{ height: '500px' }}>
        <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-white/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400">
              <BrainCircuit size={24} />
            </div>
            <div>
              <h2 className="text-lg font-bold">AI Operations Assistant</h2>
              <p className="text-xs text-gray-500">LangGraph Powered Orchestrator</p>
            </div>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50/50">
          {chatHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-4">
              <BrainCircuit size={48} className="text-slate-700" />
              <p>Ask me to analyze operations, predict delays, or send instructions to workers.</p>
              <div className="flex gap-2 text-xs">
                <span className="bg-white px-3 py-1 rounded-full border border-gray-200 cursor-pointer hover:bg-gray-100" onClick={() => setQuery("What is the current outbound status?")}>What is the outbound status?</span>
                <span className="bg-white px-3 py-1 rounded-full border border-gray-200 cursor-pointer hover:bg-gray-100" onClick={() => setQuery("Send an instruction to W0001 to assist in picking zone A.")}>Instruct W0001</span>
              </div>
            </div>
          ) : (
            chatHistory.map((msg, idx) => (
              <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'agent' && (
                  <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 mt-1">
                    <BrainCircuit size={16} className="text-white" />
                  </div>
                )}
                <div className={`max-w-[80%] rounded-2xl p-4 ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-white border border-gray-200 text-gray-800 rounded-tl-none'}`}>
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-lg bg-blue-800 flex items-center justify-center flex-shrink-0 mt-1">
                    <User size={16} className="text-white" />
                  </div>
                )}
              </div>
            ))
          )}
          {loading && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0 mt-1">
                <BrainCircuit size={16} className="text-white" />
              </div>
              <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-none p-4 flex items-center gap-2">
                <Loader2 size={16} className="animate-spin text-indigo-400" />
                <span className="text-gray-500 text-sm">Agent is thinking...</span>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-200 bg-white">
          <div className="flex gap-4 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && askAgent()}
              placeholder="Ask a question or issue an instruction..."
              className="flex-1 bg-gray-50 border border-gray-200 rounded-xl pl-4 pr-12 py-3 focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
            />
            <button 
              onClick={askAgent}
              disabled={loading || !query.trim()}
              className="absolute right-2 top-2 bottom-2 bg-indigo-600 hover:bg-indigo-700 w-10 rounded-lg flex items-center justify-center transition-colors disabled:opacity-50 disabled:hover:bg-indigo-600"
            >
              <Send size={18} className="text-white" />
            </button>
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
