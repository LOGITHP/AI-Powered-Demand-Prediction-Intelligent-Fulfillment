import { useState, useEffect } from 'react';
import { Activity, Clock, CheckCircle, XCircle } from 'lucide-react';
import api from '../lib/api';

export default function Audit() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      const res = await api.get('/agent/audit');
      setLogs(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleApproval = async (id: number, decision: 'APPROVED' | 'REJECTED') => {
    try {
      await api.post(`/agent/audit/${id}/approval`, { decision });
      fetchLogs(); // refresh the logs
    } catch (err) {
      console.error("Failed to approve/reject", err);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <header className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Activity className="text-indigo-400" size={32} />
          Action Engine & Audit Log
        </h1>
      </header>

      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-lg p-6">
        {loading ? (
          <div className="text-gray-500 animate-pulse flex items-center gap-2">
            Loading logs...
          </div>
        ) : logs.length === 0 ? (
          <div className="text-gray-400 text-center py-8">
            No agent activity recorded yet.
          </div>
        ) : (
          <div className="space-y-4">
            {logs.map(log => (
              <div key={log.id} className="bg-gray-50 border border-gray-200 p-5 rounded-xl">
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-2">
                    <span className="bg-indigo-500/20 text-indigo-400 px-3 py-1 rounded-full text-xs font-bold uppercase">
                      {log.tool_called || 'REASONING'}
                    </span>
                    <span className="text-gray-500 text-sm flex items-center gap-1">
                      <Clock size={14} /> {new Date(log.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {log.manager_approval === 'APPROVED' && <span className="text-green-400 text-sm flex items-center gap-1"><CheckCircle size={16}/> Approved</span>}
                    {log.manager_approval === 'REJECTED' && <span className="text-red-400 text-sm flex items-center gap-1"><XCircle size={16}/> Rejected</span>}
                    {log.manager_approval === 'PENDING' && (
                      <div className="flex items-center gap-2">
                        <button 
                          onClick={() => handleApproval(log.id, 'APPROVED')}
                          className="bg-green-100 text-green-700 hover:bg-green-200 px-3 py-1 rounded text-sm font-medium transition"
                        >
                          Approve
                        </button>
                        <button 
                          onClick={() => handleApproval(log.id, 'REJECTED')}
                          className="bg-red-100 text-red-700 hover:bg-red-200 px-3 py-1 rounded text-sm font-medium transition"
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="text-gray-800">
                    <span className="text-gray-400 font-medium text-sm">Recommendation:</span>
                    <p className="mt-1">{log.recommendation}</p>
                  </div>
                  {log.execution_result && (
                    <div className="text-gray-700 bg-white p-3 rounded-lg border border-gray-200 text-sm">
                      <span className="text-gray-400 font-medium">Result:</span> {log.execution_result}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
