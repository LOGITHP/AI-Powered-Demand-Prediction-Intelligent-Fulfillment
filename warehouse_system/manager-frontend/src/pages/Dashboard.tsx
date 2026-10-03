import { useState } from 'react';
import { BrainCircuit, Send, Loader2, Users, Package, AlertTriangle } from 'lucide-react';
import api from '../lib/api';

export default function Dashboard() {
  const [query, setQuery] = useState('');
  const [agentResponse, setAgentResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const askAgent = async () => {
    if (!query) return;
    setLoading(true);
    setAgentResponse('');
    try {
      const res = await api.post('/agent/chat', {
        message: query,
        warehouse_id: 'WH01'
      });
      setAgentResponse(res.data.response);
    } catch (err: any) {
      setAgentResponse("Error communicating with AI Agent. Is NVIDIA API Key configured?");
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <header className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-100">Operations Dashboard</h1>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-2 bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-sm font-medium">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            System Healthy
          </span>
        </div>
      </header>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 flex items-start justify-between">
          <div>
            <p className="text-slate-400 text-sm font-medium">Workforce Availability</p>
            <p className="text-3xl font-bold mt-2">42 <span className="text-sm text-slate-500 font-normal">/ 50 Present</span></p>
          </div>
          <div className="p-3 bg-blue-500/20 rounded-xl text-blue-400">
            <Users size={24} />
          </div>
        </div>
        
        <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 flex items-start justify-between">
          <div>
            <p className="text-slate-400 text-sm font-medium">Active Tasks</p>
            <p className="text-3xl font-bold mt-2">1,204 <span className="text-sm text-slate-500 font-normal">Pending</span></p>
          </div>
          <div className="p-3 bg-purple-500/20 rounded-xl text-purple-400">
            <Package size={24} />
          </div>
        </div>
        
        <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 flex items-start justify-between">
          <div>
            <p className="text-slate-400 text-sm font-medium">ML Delay Risk</p>
            <p className="text-3xl font-bold mt-2 text-yellow-400">14% <span className="text-sm text-slate-500 font-normal text-slate-400">Probability</span></p>
          </div>
          <div className="p-3 bg-yellow-500/20 rounded-xl text-yellow-400">
            <AlertTriangle size={24} />
          </div>
        </div>
      </div>

      {/* LangGraph Agent Section */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400">
              <BrainCircuit size={24} />
            </div>
            <h2 className="text-xl font-bold">Ask LangGraph Agent</h2>
          </div>
        </div>
        
        <div className="p-6 space-y-4">
          <div className="flex gap-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && askAgent()}
              placeholder="e.g. What is the current warehouse status? or Analyze picking labour requirements."
              className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none"
            />
            <button 
              onClick={askAgent}
              disabled={loading}
              className="bg-indigo-600 hover:bg-indigo-700 px-6 py-3 rounded-xl font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="animate-spin" /> : <Send size={20} />}
              Ask Agent
            </button>
          </div>
          
          {agentResponse && (
            <div className="mt-6 bg-slate-900 border border-slate-700 rounded-xl p-6">
              <h3 className="text-indigo-400 font-medium mb-3 flex items-center gap-2">
                <BrainCircuit size={18} />
                Agent Analysis
              </h3>
              <div className="text-slate-300 leading-relaxed whitespace-pre-wrap">
                {agentResponse}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
