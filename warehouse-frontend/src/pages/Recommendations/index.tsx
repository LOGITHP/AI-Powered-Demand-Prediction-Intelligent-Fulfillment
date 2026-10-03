import { useState } from 'react';
import { Brain, MessageSquare, AlertTriangle, Send, Loader2, Sparkles, CheckCircle2 } from 'lucide-react';
import { api, USE_MOCK } from '../../services/api';

interface AgentResponse {
  response: string;
  severity: string;
  recommendations: string[];
  reasoning: string;
}

export default function Recommendations() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [error, setError] = useState('');

  const askAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setError('');
    
    try {
      if (USE_MOCK) {
        // Mock response
        setTimeout(() => {
          setResult({
            response: "Based on the current workload, we need to redistribute our workforce.",
            severity: "medium",
            recommendations: [
              "Move 3 workers from Inbound to Outbound.",
              "Prioritize picking for order batch #892."
            ],
            reasoning: "Outbound picking is experiencing a 15% delay while Inbound is currently operating at 40% capacity."
          });
          setLoading(false);
        }, 1500);
        return;
      }
      
      const res = await api.post('/api/query', { query });
      setResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to communicate with NVIDIA Agent API.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 font-sans h-[calc(100vh-64px)] flex flex-col">
      <div className="flex flex-col mb-2 shrink-0">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-3">
          <Brain className="text-indigo-600" size={32} /> 
          NVIDIA AI Recommendations
        </h1>
        <p className="text-slate-500 mt-2 font-medium">
          Ask the reasoning engine about current warehouse operations and get data-driven recommendations.
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col flex-1">
        {/* Chat / Results Area */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50">
          {!result && !loading && !error && (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-4">
              <Sparkles size={48} className="text-indigo-200" />
              <p className="font-semibold text-lg text-slate-500">Ask a question to begin</p>
              <div className="flex gap-2 text-sm text-slate-500">
                <span className="bg-white border border-slate-200 px-3 py-1.5 rounded-full cursor-pointer hover:border-indigo-300 hover:text-indigo-600 transition-colors" onClick={() => setQuery("Do we have enough workers for outbound?")}>
                  Do we have enough workers for outbound?
                </span>
                <span className="bg-white border border-slate-200 px-3 py-1.5 rounded-full cursor-pointer hover:border-indigo-300 hover:text-indigo-600 transition-colors" onClick={() => setQuery("Any inventory risks today?")}>
                  Any inventory risks today?
                </span>
              </div>
            </div>
          )}

          {loading && (
            <div className="h-full flex flex-col items-center justify-center space-y-4">
              <Loader2 size={40} className="text-indigo-600 animate-spin" />
              <p className="text-indigo-600 font-bold animate-pulse">NVIDIA LLM is analyzing warehouse state...</p>
            </div>
          )}

          {error && (
            <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="text-rose-600 shrink-0" />
              <div>
                <h4 className="font-bold text-rose-800">Connection Error</h4>
                <p className="text-sm text-rose-600 mt-1">{error}</p>
              </div>
            </div>
          )}

          {result && !loading && (
            <div className="space-y-6">
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                  <MessageSquare size={18} className="text-indigo-600" />
                  <h3 className="font-extrabold text-slate-900">Answer</h3>
                </div>
                <p className="text-slate-700 font-medium">{result.response}</p>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                <div className="flex items-center gap-2 mb-3">
                  <Brain size={18} className="text-indigo-600" />
                  <h3 className="font-extrabold text-slate-900">Reasoning</h3>
                </div>
                <p className="text-slate-700 font-medium leading-relaxed">{result.reasoning}</p>
              </div>

              <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Sparkles size={18} className="text-indigo-600" />
                    <h3 className="font-extrabold text-indigo-900">Actionable Recommendations</h3>
                  </div>
                  <span className={`text-xs font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                    result.severity === 'high' ? 'bg-rose-200 text-rose-800' : 
                    result.severity === 'medium' ? 'bg-amber-200 text-amber-800' : 
                    'bg-emerald-200 text-emerald-800'
                  }`}>
                    {result.severity} Priority
                  </span>
                </div>
                <div className="space-y-3">
                  {result.recommendations.map((rec, i) => (
                    <div key={i} className="flex items-start gap-3 bg-white/60 p-3 rounded-lg border border-indigo-100/50">
                      <CheckCircle2 size={18} className="text-indigo-500 shrink-0 mt-0.5" />
                      <span className="text-indigo-900 font-bold">{rec}</span>
                    </div>
                  ))}
                </div>
                {result.recommendations.length > 0 && (
                  <div className="mt-5 flex justify-end">
                    <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded-lg font-bold text-sm shadow-sm transition-colors">
                      Execute All Recommendations
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white border-t border-slate-200 shrink-0">
          <form onSubmit={askAgent} className="relative flex items-center">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask the NVIDIA reasoning engine..."
              className="w-full pl-5 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium text-slate-800"
              disabled={loading}
            />
            <button 
              type="submit"
              disabled={!query.trim() || loading}
              className="absolute right-2 p-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors shadow-sm"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
