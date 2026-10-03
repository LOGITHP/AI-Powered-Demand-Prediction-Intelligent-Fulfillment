import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import api from '../lib/api';

export default function Forecasting() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.get('/ps/forecasting').then(res => setData(res.data)).catch(console.error);
  }, []);

  if (!data) return <div className="p-8">Loading forecast data...</div>;

  return (
    <div className="space-y-8 max-w-6xl mx-auto text-gray-900">
      <h1 className="text-3xl font-bold">Volume Forecasting & Workload Projection</h1>
      
      {/* SECTION 1 - INBOUND */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4 text-blue-900">INBOUND SHIPMENT VOLUME FORECAST</h2>
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="p-4 bg-blue-50 rounded-lg"><p className="text-sm text-gray-500">Predicted</p><p className="text-2xl font-bold">{data.inbound.predicted}</p></div>
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Historical Avg</p><p className="text-2xl font-bold">{data.inbound.hist_avg}</p></div>
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Current</p><p className="text-2xl font-bold">{data.inbound.current}</p></div>
          <div className="p-4 bg-green-50 rounded-lg"><p className="text-sm text-gray-500">Change</p><p className="text-2xl font-bold text-green-600">+{data.inbound.change_pct}%</p></div>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.inbound.chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="historical" stroke="#9ca3af" name="Historical" />
              <Line type="monotone" dataKey="predicted" stroke="#3b82f6" name="Predicted" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SECTION 2 - OUTBOUND */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4 text-purple-900">OUTBOUND ORDER VOLUME FORECAST</h2>
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="p-4 bg-purple-50 rounded-lg"><p className="text-sm text-gray-500">Predicted Orders</p><p className="text-2xl font-bold">{data.outbound.predicted}</p></div>
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Current Orders</p><p className="text-2xl font-bold">{data.outbound.current}</p></div>
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Historical Avg</p><p className="text-2xl font-bold">{data.outbound.hist_avg}</p></div>
          <div className="p-4 bg-red-50 rounded-lg"><p className="text-sm text-gray-500">Change</p><p className="text-2xl font-bold text-red-600">{data.outbound.change_pct}%</p></div>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.outbound.chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="historical" stroke="#9ca3af" name="Historical" />
              <Line type="monotone" dataKey="predicted" stroke="#8b5cf6" name="Predicted" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SECTION 3 - INVENTORY */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4 text-green-900">INVENTORY MOVEMENT FORECAST</h2>
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Current Inventory</p><p className="text-2xl font-bold">{data.inventory.current}</p></div>
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Predicted Movement</p><p className="text-2xl font-bold">{data.inventory.predicted_move}</p></div>
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Expected Change</p><p className="text-2xl font-bold">{data.inventory.expected_change}</p></div>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.inventory.chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="inbound" fill="#3b82f6" name="Inbound" />
              <Bar dataKey="outbound" fill="#8b5cf6" name="Outbound" />
              <Bar dataKey="net" fill="#10b981" name="Net" />
              <Bar dataKey="predicted" fill="#f59e0b" name="Predicted" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SECTION 4 - WORKLOAD */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4 text-orange-900">WORKLOAD PROJECTION</h2>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-4 mb-6">
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Current</p><p className="text-xl font-bold">{data.workload.current}</p></div>
          <div className="p-4 bg-blue-50 rounded-lg"><p className="text-sm text-gray-500">Forecasted</p><p className="text-xl font-bold">{data.workload.forecast}</p></div>
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Inbound</p><p className="text-xl font-bold">{data.workload.inbound}</p></div>
          <div className="p-4 bg-gray-50 rounded-lg"><p className="text-sm text-gray-500">Outbound</p><p className="text-xl font-bold">{data.workload.outbound}</p></div>
          <div className="p-4 bg-orange-50 rounded-lg"><p className="text-sm text-gray-500">Peak</p><p className="text-xl font-bold">{data.workload.peak}</p></div>
          <div className="p-4 bg-green-50 rounded-lg"><p className="text-sm text-gray-500">Req Workers</p><p className="text-xl font-bold">{data.workload.workers}</p></div>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.workload.chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="step" dataKey="actual" stroke="#9ca3af" name="ACTUAL" strokeWidth={2} />
              <Line type="step" dataKey="forecast" stroke="#ef4444" name="FORECAST" strokeWidth={2} strokeDasharray="5 5" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
