import { useState } from 'react';
import { BrainCircuit, Loader2, Send, User } from 'lucide-react';
import api from '../lib/api';

export default function AIAgent() {
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState<{role: 'user'|'agent', content: string}[]>([]);
  const [loading, setLoading] = useState(false);

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
    <div className="space-y-6 max-w-6xl mx-auto h-[calc(100vh-8rem)]">
      <header className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">AI Operations Assistant</h1>
      </header>

      {/* LangGraph Agent Chat Interface */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-lg flex flex-col h-full">
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
    </div>
  );
}
