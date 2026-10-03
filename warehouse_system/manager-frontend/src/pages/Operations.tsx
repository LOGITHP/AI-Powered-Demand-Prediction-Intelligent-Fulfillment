import { useState, useEffect } from 'react';
import { Send, ArrowRightCircle, CheckCircle, PackageOpen, ClipboardList } from 'lucide-react';
import api from '../lib/api';

export default function Operations() {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const [inboundItems, setInboundItems] = useState(100);
  const [inboundPriority, setInboundPriority] = useState('NORMAL');

  const [outboundItems, setOutboundItems] = useState(50);
  const [outboundPriority, setOutboundPriority] = useState('NORMAL');

  useEffect(() => {
    // We assume /api/inbound/products exists or we can just mock product ID 1 for testing since the seed creates it
    // Using a simple fetch just in case we add products endpoint later
    api.get('/inbound/products').catch(() => {});
  }, []);

  const handleCreateShipment = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    try {
      const payload = {
        supplier: "Global Supplying Co.",
        vehicle_number: "TRK-001",
        driver_name: "John Smith",
        expected_arrival: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
        priority: inboundPriority,
        items: [
          {
            product_id: 1, // Assume seeded product 1
            expected_quantity: Number(inboundItems)
          }
        ]
      };
      const res = await api.post('/inbound/shipments', payload);
      setMessage(`Inbound Shipment ${res.data.shipment_id} created successfully.`);
    } catch (err: any) {
      setMessage(err.response?.data?.detail || 'Failed to create shipment');
    }
    setLoading(false);
  };

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    try {
      const payload = {
        customer: "Retail Chain B",
        priority: outboundPriority,
        required_dispatch_time: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
        items: [
          {
            product_id: 1, // Assume seeded product 1
            required_quantity: Number(outboundItems)
          }
        ]
      };
      const res = await api.post('/outbound/orders', payload);
      setMessage(`Outbound Order ${res.data.order_id} created successfully.`);
    } catch (err: any) {
      setMessage(err.response?.data?.detail || 'Failed to create order');
    }
    setLoading(false);
  };

  const [pendingOrders, setPendingOrders] = useState<any[]>([]);

  const fetchPendingOrders = async () => {
    try {
      const res = await api.get('/outbound/orders?status_filter=CREATED');
      setPendingOrders(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchPendingOrders();
    const interval = setInterval(fetchPendingOrders, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleReleaseOrder = async (orderId: string) => {
    try {
      await api.post(`/outbound/orders/${orderId}/release`);
      fetchPendingOrders();
      setMessage(`Order ${orderId} released successfully.`);
    } catch (err: any) {
      setMessage(err.response?.data?.detail || `Failed to release order ${orderId}`);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 mb-10">
      <header>
        <h1 className="text-3xl font-bold text-gray-900">Workload Management (Order & Shipment Creation)</h1>
        <p className="text-gray-500 mt-2">Generate and inject real Inbound Shipments and Outbound Orders into the system to drive the state machine.</p>
      </header>

      {message && (
        <div className="p-4 bg-green-50 text-green-700 rounded-xl flex items-center gap-2 border border-green-200">
          <CheckCircle size={18} />
          {message}
        </div>
      )}

      <div className="bg-white border border-gray-200 p-6 rounded-2xl shadow-sm mt-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <ArrowRightCircle className="text-purple-400" /> 
            Manager Action: Release Orders
          </h2>
          <p className="text-sm text-gray-500 mb-4 leading-relaxed">
            New Outbound Orders are in <b>CREATED</b> state. The manager must release them to the floor for picking. This step checks inventory availability and reserves stock.
          </p>
          
          <div className="space-y-3">
            {pendingOrders.length === 0 ? (
              <div className="p-4 text-center text-gray-500 bg-gray-50 rounded-lg">No pending orders to release.</div>
            ) : (
              pendingOrders.map(order => (
                <div key={order.id} className="p-4 border border-gray-200 rounded-lg flex items-center justify-between">
                  <div>
                    <div className="font-bold">{order.order_id}</div>
                    <div className="text-sm text-gray-500">Customer: {order.customer} | Items: {order.total_items}</div>
                  </div>
                  <button 
                    onClick={() => handleReleaseOrder(order.order_id)}
                    className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    Release to Floor
                  </button>
                </div>
              ))
            )}
          </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        {/* INBOUND */}
        <div className="bg-white border border-gray-200 p-6 rounded-2xl">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
            <PackageOpen className="text-blue-500" /> 
            Create Inbound Shipment
          </h2>
          
          <form onSubmit={handleCreateShipment} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-2">Priority</label>
              <select 
                value={inboundPriority}
                onChange={(e) => setInboundPriority(e.target.value)}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-blue-500"
              >
                <option value="LOW">Low</option>
                <option value="NORMAL">Normal</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-500 mb-2">Item Quantity (Product ID 1)</label>
              <input 
                type="number"
                min="1"
                value={inboundItems}
                onChange={(e) => setInboundItems(parseInt(e.target.value))}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-blue-500"
              />
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-xl font-medium flex justify-center items-center gap-2 mt-4"
            >
              {loading ? 'Processing...' : <><Send size={18} /> Create Shipment</>}
            </button>
          </form>
        </div>

        {/* OUTBOUND */}
        <div className="bg-white border border-gray-200 p-6 rounded-2xl">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
            <ClipboardList className="text-orange-500" /> 
            Create Outbound Order
          </h2>
          
          <form onSubmit={handleCreateOrder} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-2">Priority</label>
              <select 
                value={outboundPriority}
                onChange={(e) => setOutboundPriority(e.target.value)}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-orange-500"
              >
                <option value="LOW">Low</option>
                <option value="NORMAL">Normal</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-500 mb-2">Required Quantity (Product ID 1)</label>
              <input 
                type="number"
                min="1"
                value={outboundItems}
                onChange={(e) => setOutboundItems(parseInt(e.target.value))}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-orange-500"
              />
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-orange-500 hover:bg-orange-600 text-white py-3 rounded-xl font-medium flex justify-center items-center gap-2 mt-4"
            >
              {loading ? 'Processing...' : <><Send size={18} /> Create Order</>}
            </button>
          </form>
        </div>

      </div>


    </div>
  );
}
