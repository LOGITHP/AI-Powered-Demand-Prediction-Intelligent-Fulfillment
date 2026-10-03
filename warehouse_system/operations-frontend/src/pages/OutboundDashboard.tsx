import { useState, useEffect } from 'react';
import { PackageSearch, CheckCircle2, AlertTriangle, Bell, Send, Check } from 'lucide-react';
import api from '../lib/api';

export default function OutboundDashboard() {
  const [activeTask, setActiveTask] = useState<any>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [replyText, setReplyText] = useState('');

  const fetchNotifications = async () => {
    try {
      const res = await api.get('/notifications');
      setNotifications(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleReply = async (id: number) => {
    if (!replyText) return;
    try {
      await api.post(`/notifications/${id}/reply`, { reply: replyText });
      setReplyText('');
      fetchNotifications();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAcknowledge = async (id: number) => {
    try {
      await api.post(`/notifications/${id}/read`);
      fetchNotifications();
    } catch (err) {
      console.error(err);
    }
  };

  const getTask = async () => {
    try {
      const res = await api.get('/workload/tasks/next');
      if (res.data.id) {
        setActiveTask(res.data);
      } else {
        alert("No tasks currently available in the queue.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const completeTask = async () => {
    if (!activeTask) return;
    try {
      await api.post(`/workload/tasks/${activeTask.id}/complete`);
      setActiveTask(null);
    } catch (err) {
      console.error(err);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      
      {/* Notifications Panel */}
      {notifications.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
          <div className="bg-gray-50 border-b border-gray-200 p-4 flex items-center justify-between">
            <h3 className="font-bold flex items-center gap-2">
              <Bell size={20} className="text-blue-400" />
              Agent Instructions & Alerts
            </h3>
            {unreadCount > 0 && (
              <span className="bg-blue-600 text-white text-xs px-2 py-1 rounded-full">{unreadCount} New</span>
            )}
          </div>
          <div className="divide-y divide-gray-200 max-h-80 overflow-y-auto">
            {notifications.map((notif) => (
              <div key={notif.id} className={`p-4 ${!notif.is_read ? 'bg-blue-900/10' : ''}`}>
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-xs font-bold px-2 py-1 rounded ${notif.type === 'INSTRUCTION' ? 'bg-purple-500/20 text-purple-400' : 'bg-gray-100 text-gray-700'}`}>
                    {notif.type}
                  </span>
                  <span className="text-xs text-gray-400">{new Date(notif.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-gray-800 mb-3">{notif.message}</p>
                
                {notif.type === 'INSTRUCTION' && !notif.reply_message ? (
                  <div className="flex gap-2 mt-3">
                    <input
                      type="text"
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      placeholder="Reply to agent..."
                      className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                    />
                    <button onClick={() => handleReply(notif.id)} className="bg-blue-600 hover:bg-blue-700 p-2 rounded-lg text-white">
                      <Send size={16} />
                    </button>
                  </div>
                ) : notif.reply_message ? (
                  <div className="mt-3 bg-gray-50 p-3 rounded-lg border border-gray-200">
                    <p className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Check size={12} className="text-green-400" /> You replied:</p>
                    <p className="text-sm text-gray-700">{notif.reply_message}</p>
                  </div>
                ) : !notif.is_read ? (
                  <button onClick={() => handleAcknowledge(notif.id)} className="mt-2 text-blue-400 text-sm font-medium hover:text-blue-300">
                    Acknowledge
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      )}

      {!activeTask ? (
        <div className="bg-white border border-gray-200 rounded-2xl p-8 text-center">
          <div className="mx-auto w-20 h-20 bg-blue-500/20 rounded-full flex items-center justify-center mb-4">
            <PackageSearch size={40} className="text-blue-400" />
          </div>
          <h2 className="text-2xl font-bold mb-2">Ready for Outbound Dispatch</h2>
          <p className="text-gray-500 mb-8">You currently have no outbound delivery tasks.</p>
          
          <button 
            onClick={getTask}
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-xl text-lg font-medium transition-colors"
          >
            Get Next Task
          </button>
        </div>
      ) : (
        <div className="bg-white border border-blue-500/50 rounded-2xl overflow-hidden shadow-[0_0_15px_rgba(59,130,246,0.1)]">
          <div className="bg-blue-600/20 border-b border-blue-500/30 p-6 flex justify-between items-center">
            <div>
              <span className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded mb-2 inline-block">
                {activeTask.priority} PRIORITY
              </span>
              <h2 className="text-2xl font-bold text-blue-400">{activeTask.id}</h2>
              <p className="text-gray-700">{activeTask.type}</p>
            </div>
            <div className="text-right">
              <p className="text-gray-500 text-sm">Target Time</p>
              <p className="text-xl font-bold font-mono">14:30</p>
            </div>
          </div>
          
          <div className="p-6 grid grid-cols-2 gap-6">
            <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
              <p className="text-sm text-gray-500 mb-1">Location</p>
              <p className="text-2xl font-bold">{activeTask.location}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
              <p className="text-sm text-gray-500 mb-1">Items to Pick</p>
              <p className="text-2xl font-bold">{activeTask.items}</p>
            </div>
          </div>
          
          <div className="p-6 pt-0 flex gap-4">
            <button className="flex-1 bg-gray-100 hover:bg-gray-200 px-4 py-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors">
              <AlertTriangle size={20} className="text-yellow-400" />
              Report Issue
            </button>
            <button 
              onClick={completeTask}
              className="flex-[2] bg-green-600 hover:bg-green-700 px-4 py-4 rounded-xl font-medium flex items-center justify-center gap-2 text-lg transition-colors shadow-lg"
            >
              <CheckCircle2 size={24} />
              Confirm Complete
            </button>
          </div>
        </div>
      )}
      
    </div>
  );
}
