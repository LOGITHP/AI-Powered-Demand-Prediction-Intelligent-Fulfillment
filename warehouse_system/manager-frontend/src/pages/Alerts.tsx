import { useState, useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import api from '../lib/api';

export default function Alerts() {
  const [approvals, setApprovals] = useState<any[]>([]);

  useEffect(() => {
    fetchApprovals();
    const interval = setInterval(fetchApprovals, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchApprovals = async () => {
    try {
      const res = await api.get('/approvals');
      setApprovals(res.data);
    } catch(err) {
      console.error(err);
    }
  };

  const handleApproval = async (id: number, status: string) => {
    let reason = "";
    if (status === 'REJECTED') {
      const input = prompt("Please provide a reason for declining this action:");
      if (input === null) return; // Cancelled
      reason = input;
    }
    
    try {
      await api.put(`/approvals/${id}`, { status, reason });
      fetchApprovals();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <header className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Alerts & Approvals</h1>
      </header>

      {approvals.length > 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm p-6">
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
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm p-12 text-center flex flex-col items-center">
            <AlertTriangle size={48} className="text-gray-300 mb-4" />
            <h3 className="text-xl font-bold text-gray-700">No Pending Alerts</h3>
            <p className="text-gray-500 mt-2">There are currently no alerts or approvals requiring your attention.</p>
        </div>
      )}
    </div>
  );
}
