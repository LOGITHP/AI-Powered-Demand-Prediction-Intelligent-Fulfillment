import { useState, useEffect } from 'react';
import { PackageOpen, Bell, Check, TrendingUp, Clock, Boxes, Truck, AlertCircle } from 'lucide-react';
import api from '../lib/api';

export default function InboundDashboard() {
  const [shipments, setShipments] = useState<any[]>([]);
  const [kpis, setKpis] = useState<any>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [replyText, setReplyText] = useState('');
  const [decliningId, setDecliningId] = useState<number | null>(null);
  const [declineReason, setDeclineReason] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [shipRes, kpiRes, notifRes] = await Promise.all([
        api.get('/inbound/shipments'),
        api.get('/inbound/kpis'),
        api.get('/notifications')
      ]);
      setShipments(shipRes.data);
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

  const handleAction = async (shipmentId: string, action: string, payload: any = {}) => {
    try {
      await api.post(`/inbound/shipments/${shipmentId}/${action}`, payload);
      fetchData();
    } catch (err) {
      alert("Error performing action: " + ((err as any).response?.data?.detail || (err as any).message));
    }
  };

  const handleArrive = (id: string) => handleAction(id, 'arrive', { actual_arrival: new Date().toISOString() });
  const handleStartReceiving = (id: string) => handleAction(id, 'start-receiving');
  
  const handleCompleteReceiving = async (id: string) => {
    try {
      const res = await api.get(`/inbound/shipments/${id}/items`);
      const items = res.data;
      const updates = items.map((item: any) => ({
        item_id: item.id,
        received_quantity: item.expected_quantity, // Simplified for UI
        damaged_quantity: 0
      }));
      await handleAction(id, 'complete-receiving', { updates });
    } catch(err) {}
  };

  const handleCompleteInspection = async (id: string) => {
    try {
      const res = await api.get(`/inbound/shipments/${id}/items`);
      const items = res.data;
      const updates = items.map((item: any) => ({
        item_id: item.id,
        inspection_status: 'ACCEPTED',
        damaged_quantity: 0,
        rejected_quantity: 0
      }));
      await handleAction(id, 'complete-inspection', { updates });
    } catch(err) {}
  };

  const handleCompletePutaway = async (id: string) => {
    try {
      const res = await api.get(`/inbound/shipments/${id}/items`);
      const items = res.data;
      // In a real app we'd ask the user to select locations. 
      // For now we assume a default location id 1 exists (from seed).
      const assignments = items.map((item: any) => ({
        item_id: item.id,
        location_id: 1, 
        quantity: item.accepted_quantity
      }));
      await handleAction(id, 'complete-putaway', { assignments });
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
            <TrendingUp size={18} className="text-blue-500" />
            <span className="text-xs text-gray-500 font-medium">Total Shipments Today</span>
          </div>
          <p className="text-2xl font-bold text-gray-800">{kpis?.total_shipments_today || 0}</p>
          <p className="text-xs text-gray-400 mt-1">{kpis?.completed_today || 0} completed</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Boxes size={18} className="text-green-500" />
            <span className="text-xs text-gray-500 font-medium">Items Received</span>
          </div>
          <p className="text-2xl font-bold text-green-600">{kpis?.receiving_throughput || 0}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Truck size={18} className="text-orange-500" />
            <span className="text-xs text-gray-500 font-medium">In Queue</span>
          </div>
          <p className="text-2xl font-bold text-orange-600">{kpis?.in_queue || 0}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={18} className="text-purple-500" />
            <span className="text-xs text-gray-500 font-medium">Delayed</span>
          </div>
          <p className="text-2xl font-bold text-red-600">{kpis?.delayed || 0}</p>
        </div>
      </div>

      {/* Real Shipments */}
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
        <div className="bg-blue-50 border-b border-blue-100 p-4 flex items-center justify-between">
          <h3 className="font-bold text-blue-900 flex items-center gap-2">
            <PackageOpen size={20} className="text-blue-500" />
            Live Inbound Workflow
          </h3>
        </div>
        <div className="divide-y divide-gray-100">
          {shipments.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No shipments found.</div>
          ) : (
            shipments.map((ship) => (
              <div key={ship.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-gray-50">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-800">{ship.shipment_id}</span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">Supplier: {ship.supplier}</span>
                    <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded">Gate: {['North Gate', 'South Gate', 'East Gate'][ship.id % 3]}</span>
                    {ship.status === 'EXPECTED' && (
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded border border-yellow-200">
                        Pre-arrival Info Needed
                      </span>
                    )}
                    {ship.delay_risk !== 'LOW' && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded flex items-center gap-1">
                        <AlertCircle size={12}/> High Risk
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    Status: <span className="font-semibold text-blue-600">{ship.status}</span>
                    <span className="mx-2">•</span>
                    Expected: {new Date(ship.expected_arrival).toLocaleTimeString()}
                    <span className="mx-2">•</span>
                    Items: {ship.total_items}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {ship.status === 'EXPECTED' && (
                    <button onClick={() => handleArrive(ship.shipment_id)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Mark Arrived</button>
                  )}
                  {ship.status === 'ARRIVED' && (
                    <button onClick={() => handleStartReceiving(ship.shipment_id)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Start Receiving</button>
                  )}
                  {ship.status === 'RECEIVING' && (
                    <button onClick={() => handleCompleteReceiving(ship.shipment_id)} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Complete Receiving (Auto)</button>
                  )}
                  {ship.status === 'INSPECTION' && (
                    <button onClick={() => handleCompleteInspection(ship.shipment_id)} className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Complete Inspection (Auto)</button>
                  )}
                  {ship.status === 'PUTAWAY' && (
                    <button onClick={() => handleCompletePutaway(ship.shipment_id)} className="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Complete Putaway (Auto)</button>
                  )}
                  {ship.status === 'COMPLETED' && (
                    <span className="text-green-600 font-bold bg-green-50 px-3 py-1 rounded-full text-sm">Completed</span>
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
              <Bell size={20} className="text-blue-500" />
              Agent Instructions & Alerts
            </h3>
            {unreadCount > 0 && (
              <span className="bg-blue-600 text-white text-xs px-2 py-1 rounded-full">{unreadCount} New</span>
            )}
          </div>
          <div className="divide-y divide-gray-200 max-h-80 overflow-y-auto">
            {notifications.map((notif) => (
              <div key={notif.id} className={`p-4 ${!notif.is_read ? 'bg-blue-50' : ''}`}>
                <div className="flex justify-between items-start mb-2">
                  <span className={`text-xs font-bold px-2 py-1 rounded ${notif.type === 'INSTRUCTION' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-700'}`}>
                    {notif.type}
                  </span>
                  <span className="text-xs text-gray-400">{new Date(notif.timestamp).toLocaleTimeString()}</span>
                </div>
                <p className="text-gray-800 mb-3">{notif.message}</p>

                {notif.type === 'INSTRUCTION' && !notif.reply_message ? (
                  <div className="mt-3">
                    <div className="text-xs text-blue-600 mb-2 font-medium flex items-center gap-1">
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
                  <button onClick={() => handleAcknowledge(notif.id)} className="mt-2 text-blue-600 text-sm font-medium hover:underline">
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
