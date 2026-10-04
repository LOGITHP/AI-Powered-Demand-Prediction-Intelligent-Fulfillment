import { useEffect, useState } from 'react';
import { AlertTriangle, Building2, Package, ShoppingCart } from 'lucide-react';
import api from '../lib/api';

interface Warehouse {
  warehouse_id: string;
  agent_id: string;
  status: string;
  last_heartbeat: string;
  capabilities: string[];
}

interface Inventory {
  available: number;
  reserved: number;
}

interface Order {
  order_id: string;
  status: string;
  destination: string;
}

export default function Dashboard() {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [inventory, setInventory] = useState<Record<string, Inventory>>({});
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const whRes = await api.get<Warehouse[]>('/api/v1/warehouses');
        setWarehouses(whRes.data);
        
        const invRes = await api.get<Record<string, Inventory>>('/api/v1/inventory');
        setInventory(invRes.data);

        const ordRes = await api.get<Order[]>('/api/v1/orders');
        setOrders(ordRes.data);
        setError(false);
      } catch (e) {
        console.error('Failed to fetch data', e);
        setError(true);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const totalInv = Object.values(inventory).reduce((acc, curr) => acc + curr.available, 0);
  const pendingOrders = orders.filter(o => o.status === 'PENDING').length;

  const stats = [
    { label: 'Warehouses Online', value: warehouses.filter(w => w.status === 'ONLINE').length, icon: Building2, color: '#00E5FF' },
    { label: 'Global Inventory', value: totalInv, icon: Package, color: '#00E5FF' },
    { label: 'Pending Orders', value: pendingOrders, icon: ShoppingCart, color: '#FFAB00' },
    { label: 'Active Alerts', value: 0, icon: AlertTriangle, color: '#FF1744' },
  ];

  return (
    <div className="min-h-screen">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">Head Office Portal</h1>
            <p className="mt-2 text-sm text-gray-500">
              Central orchestration and visibility across all mock agents.
            </p>
          </div>
          {error && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-red-50 text-red-600">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-red-400"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
              </span>
              <span className="text-sm font-medium">Connection Lost</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
          {stats.map((item) => (
            <div key={item.label} className="p-6 bg-white rounded-2xl border border-gray-100 shadow-sm">
              <div className="flex items-center">
                <div className="p-3 rounded-xl" style={{ backgroundColor: `${item.color}20` }}>
                  <item.icon className="w-6 h-6" style={{ color: item.color }} />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">{item.label}</dt>
                    <dd className="text-2xl font-bold text-gray-900 mt-1">{item.value}</dd>
                  </dl>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-8">
            <div className="p-6 bg-white rounded-2xl border border-gray-100 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-indigo-600" />
                Connected Warehouse Agents
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {warehouses.map((wh) => (
                  <div key={wh.warehouse_id} className="p-5 bg-gray-50 rounded-2xl border border-gray-100">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-gray-900">{wh.warehouse_id}</h3>
                      <span className={`text-xs font-semibold px-2 py-1 rounded ${wh.status === 'ONLINE' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                        {wh.status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      <p>Agent ID: {wh.agent_id}</p>
                      <p>Last Heartbeat: {new Date(wh.last_heartbeat).toLocaleTimeString()}</p>
                    </div>
                  </div>
                ))}
                {warehouses.length === 0 && <div className="text-gray-500 p-4">No agents connected.</div>}
              </div>
            </div>

            <div className="p-6 bg-white rounded-2xl border border-gray-100 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
                <ShoppingCart className="w-5 h-5 text-indigo-600" />
                Recent Orders
              </h2>
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-500">Order ID</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-500">Destination</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-500">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.slice(0, 5).map(o => (
                      <tr key={o.order_id} className="border-b border-gray-100">
                        <td className="px-4 py-4 text-sm font-medium text-gray-900">{o.order_id}</td>
                        <td className="px-4 py-4 text-sm text-gray-500">{o.destination}</td>
                        <td className="px-4 py-4 text-sm">
                          <span className={o.status === 'PENDING' ? 'text-amber-600 font-medium' : 'text-green-600 font-medium'}>{o.status}</span>
                        </td>
                      </tr>
                    ))}
                    {orders.length === 0 && <tr><td colSpan={3} className="px-4 py-4 text-gray-500">No orders</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="space-y-8">
            <div className="p-6 bg-white rounded-2xl border border-gray-100 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
                <Package className="w-5 h-5 text-indigo-600" />
                Global Inventory
              </h2>
              <div className="space-y-4">
                {Object.entries(inventory).map(([prodId, data]) => (
                  <div key={prodId} className="flex justify-between items-center border-b border-gray-100 pb-2">
                    <span className="text-gray-600 font-medium">{prodId}</span>
                    <span className="font-bold text-gray-900">{data.available}</span>
                  </div>
                ))}
                {Object.keys(inventory).length === 0 && <div className="text-gray-500">No inventory data.</div>}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
