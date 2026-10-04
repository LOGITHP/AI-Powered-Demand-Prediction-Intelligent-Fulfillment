import { useState, useEffect } from 'react';
import { PackageCheck, Bell, Check, TrendingDown, Truck, Boxes, ClipboardList, AlertCircle, Clock } from 'lucide-react';
import api from '../lib/api';

export default function OutboundDashboard() {
  const [orders, setOrders] = useState<any[]>([]);
  const [kpis, setKpis] = useState<any>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [replyText, setReplyText] = useState('');
  const [decliningId, setDecliningId] = useState<number | null>(null);
  const [declineReason, setDeclineReason] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [orderRes, kpiRes, notifRes] = await Promise.all([
        api.get('/outbound/orders'),
        api.get('/outbound/kpis'),
        api.get('/notifications')
      ]);
      setOrders(orderRes.data);
      setKpis(kpiRes.data);
      setNotifications(notifRes.data);
    } catch (err) {
      console.error('Error fetching data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (orderId: string, action: string, payload: any = {}) => {
    try {
      await api.post(`/outbound/orders/${orderId}/${action}`, payload);
      fetchData();
    } catch (err) {
      alert("Error performing action: " + ((err as any).response?.data?.detail || (err as any).message));
    }
  };

  const handleStartPicking = (id: string) => handleAction(id, 'start-picking');
  
  const handleCompletePicking = async (id: string) => {
    try {
      const res = await api.get(`/outbound/orders/${id}`);
      const items = res.data.items;
      const updates = items.map((item: any) => ({
        item_id: item.id,
        picked_quantity: item.required_quantity
      }));
      await handleAction(id, 'complete-picking', { updates });
    } catch(err) {}
  };

  const handleCompletePacking = async (id: string) => {
    try {
      const res = await api.get(`/outbound/orders/${id}`);
      const items = res.data.items;
      const updates = items.map((item: any) => ({
        item_id: item.id,
        packed_quantity: item.picked_quantity
      }));
      await handleAction(id, 'complete-packing', { updates });
    } catch(err) {}
  };

  const handleCompleteLoading = async (id: string) => {
    try {
      const res = await api.get(`/outbound/orders/${id}`);
      const items = res.data.items;
      const updates = items.map((item: any) => ({
        item_id: item.id,
        loaded_quantity: item.packed_quantity
      }));
      await handleAction(id, 'complete-loading', { updates, vehicle_reference: "TRUCK-DEFAULT" });
    } catch(err) {}
  };

  const handleReply = async (id: number, text?: string) => {
    const finalReply = text || replyText;
    if (!finalReply) return;
    try {
      await api.post(`/notifications/${id}/reply`, { reply: finalReply });
      setReplyText('');
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAcknowledge = async (id: number) => {
    try {
      await api.post(`/notifications/${id}/read`);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading && !kpis) return <div className="text-center mt-10">Loading...</div>;

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Boxes size={18} className="text-orange-500" />
            <span className="text-xs text-gray-500 font-medium">Total Orders Today</span>
          </div>
          <p className="text-2xl font-bold text-gray-800">{kpis?.total_orders_today || 0}</p>
          <p className="text-xs text-gray-400 mt-1">{kpis?.completed_today || 0} completed</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <PackageCheck size={18} className="text-green-500" />
            <span className="text-xs text-gray-500 font-medium">Items Dispatched</span>
          </div>
          <p className="text-2xl font-bold text-green-600">{kpis?.items_dispatched || 0}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown size={18} className="text-red-500" />
            <span className="text-xs text-gray-500 font-medium">In Queue</span>
          </div>
          <p className="text-2xl font-bold text-red-600">{kpis?.in_queue || 0}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Truck size={18} className="text-purple-500" />
            <span className="text-xs text-gray-500 font-medium">Delayed</span>
          </div>
          <p className="text-2xl font-bold text-purple-600">{kpis?.delayed || 0}</p>
        </div>
      </div>

      {/* Real Orders */}
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
        <div className="bg-orange-50 border-b border-orange-100 p-4 flex items-center justify-between">
          <h3 className="font-bold text-orange-900 flex items-center gap-2">
            <ClipboardList size={20} className="text-orange-500" />
            Live Outbound Workflow
          </h3>
        </div>
        <div className="divide-y divide-gray-100">
          {orders.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No outbound orders found.</div>
          ) : (
            orders.map((order) => (
              <div key={order.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-gray-50">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-800">{order.order_id}</span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">Deliver to: {order.customer || 'No Customer'}</span>
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Partner: {['FedEx', 'DHL', 'UPS', 'BlueDart', 'Amazon Logistics'][order.id % 5]}</span>
                    {order.delay_risk !== 'LOW' && order.status !== 'COMPLETED' && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded flex items-center gap-1">
                        <AlertCircle size={12}/> High Risk
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    Status: <span className="font-semibold text-orange-600">{order.status}</span>
                    <span className="mx-2">•</span>
                    Dispatch By: {new Date(order.required_dispatch_time).toLocaleTimeString()}
                    <span className="mx-2">•</span>
                    Items: {order.total_items}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {order.status === 'CREATED' && (
                    <span className="text-gray-500 text-sm italic">Waiting for Manager Release</span>
                  )}
                  {order.status === 'RELEASED' && (
                    <button onClick={() => handleStartPicking(order.order_id)} className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium">Start Picking</button>
                  )}
                  {order.status === 'PICKING' && (
                    <button onClick={() => handleCompletePicking(order.order_id)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Complete Picking (Auto)</button>
                  )}
                  {order.status === 'PACKING' && (
                    <button onClick={() => handleCompletePacking(order.order_id)} className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Complete Packing (Auto)</button>
                  )}
                  {order.status === 'LOADING' && (
                    <button onClick={() => handleCompleteLoading(order.order_id)} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Handover to Partner (Auto)</button>
                  )}
                  {order.status === 'COMPLETED' && (
                    <div className="flex flex-col items-end">
                      <span className="text-green-600 font-bold bg-green-50 px-3 py-1 rounded-full text-sm">Dispatched</span>
                      <span className="text-xs text-blue-500 mt-1 italic">Delivery in Progress...</span>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Notifications Panel */}
      {notifications.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
          <div className="bg-gray-50 border-b border-gray-200 p-4 flex items-center justify-between">
            <h3 className="font-bold flex items-center gap-2">
              <Bell size={20} className="text-orange-500" />
              Agent Instructions & Alerts
            </h3>
            {unreadCount > 0 && (
              <span className="bg-orange-500 text-white text-xs px-2 py-1 rounded-full">{unreadCount} New</span>
            )}
          </div>
          <div className="divide-y divide-gray-200 max-h-80 overflow-y-auto">
            {notifications.map((notif) => (
              <div key={notif.id} className={`p-4 ${!notif.is_read ? 'bg-orange-50' : ''}`}>
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-xs font-bold px-2 py-1 rounded ${notif.type === 'INSTRUCTION' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-700'}`}>
                    {notif.type}
                  </span>
                  <span className="text-xs text-gray-400">{new Date(notif.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-gray-800 mb-3">{notif.message}</p>

                {notif.type === 'INSTRUCTION' && !notif.reply_message ? (
                  <div className="mt-3">
                    <div className="text-xs text-orange-500 mb-2 font-medium flex items-center gap-1">
                      <Clock size={12} /> Estimated Task Duration: {Math.max(5, (notif.message.length % 20) + 10)} mins
                    </div>
                    
                    {decliningId === notif.id ? (
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={declineReason}
                          onChange={(e) => setDeclineReason(e.target.value)}
                          placeholder="Reason for declining..."
                          className="flex-1 bg-gray-50 border border-red-200 rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-red-500 outline-none"
                          autoFocus
                        />
                        <button onClick={() => {
                          setDecliningId(null);
                          setDeclineReason('');
                          handleReply(notif.id, "Declined: " + declineReason);
                        }} className="bg-red-600 hover:bg-red-700 px-3 py-2 rounded-lg text-white font-medium text-sm whitespace-nowrap">
                          Submit Decline
                        </button>
                        <button onClick={() => setDecliningId(null)} className="text-gray-500 text-sm hover:underline px-2">Cancel</button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button onClick={() => {
                          handleReply(notif.id, "Accepted & Started");
                        }} className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-white font-medium text-sm flex-1 flex items-center justify-center gap-2">
                          <Check size={16} /> Accept & Start
                        </button>
                        <button onClick={() => setDecliningId(notif.id)} className="bg-gray-200 hover:bg-gray-300 px-4 py-2 rounded-lg text-gray-700 font-medium text-sm flex-1">
                          Decline
                        </button>
                      </div>
                    )}
                  </div>
                ) : notif.reply_message ? (
                  <div className="mt-3 bg-gray-50 p-3 rounded-lg border border-gray-200">
                    <p className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Check size={12} className="text-green-500" /> You replied:</p>
                    <p className="text-sm text-gray-700">{notif.reply_message}</p>
                  </div>
                ) : !notif.is_read ? (
                  <button onClick={() => handleAcknowledge(notif.id)} className="mt-2 text-orange-500 text-sm font-medium hover:underline">
                    Acknowledge
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
