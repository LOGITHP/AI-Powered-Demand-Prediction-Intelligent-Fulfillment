import { useState, useEffect } from 'react';
import { XAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import api from '../lib/api';

export default function Analytics() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.get('/ps/analytics').then(res => setData(res.data)).catch(console.error);
  }, []);

  if (!data) return <div className="p-8">Loading analytics data...</div>;

  return (
    <div className="space-y-8 max-w-6xl mx-auto text-gray-900">
      <h1 className="text-3xl font-bold">Operations Efficiency Dashboard</h1>

      {/* SECTION 1 - KPIs & BENCHMARKING */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4 text-blue-900">KPI vs BENCHMARK</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
          {data.kpis.map((kpi: any, i: number) => (
            <div key={i} className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-sm text-gray-500 font-medium mb-1">{kpi.name}</p>
              <div className="flex justify-between items-baseline mb-2">
                <span className="text-2xl font-bold">{kpi.actual}</span>
                <span className={"text-sm font-bold " + (kpi.status === 'GOOD' ? "text-green-600" : "text-red-600")}>
                  {kpi.variance}
                </span>
              </div>
              <p className="text-xs text-gray-400">Benchmark: {kpi.benchmark} | Status: <span className={kpi.status === 'GOOD' ? 'text-green-600' : 'text-red-600'}>{kpi.status}</span></p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* SECTION 2 - INBOUND */}
        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-bold mb-4">INBOUND OPERATIONS</h2>
          <div className="space-y-3 mb-6">
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Receiving Throughput</span><span className="font-bold">{data.inbound.throughput} units/hr</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Receiving Cycle Time</span><span className="font-bold">{data.inbound.receiving_ct} min</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Inspection Cycle Time</span><span className="font-bold">{data.inbound.inspection_ct} min</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Putaway Cycle Time</span><span className="font-bold">{data.inbound.putaway_ct} min</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Inbound Queue</span><span className="font-bold">{data.inbound.queue} units</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Receiving Utilization</span><span className="font-bold">{data.inbound.utilization}%</span></div>
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.inbound.chart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <Tooltip />
                <Area type="monotone" dataKey="throughput" stroke="#3b82f6" fill="#bfdbfe" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* SECTION 3 - OUTBOUND */}
        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-bold mb-4">OUTBOUND OPERATIONS</h2>
          <div className="space-y-3 mb-6">
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Picking Throughput</span><span className="font-bold">{data.outbound.picking_tp} units/hr</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Packing Throughput</span><span className="font-bold">{data.outbound.packing_tp} units/hr</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Loading Throughput</span><span className="font-bold">{data.outbound.loading_tp} units/hr</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Picking Cycle Time</span><span className="font-bold">{data.outbound.picking_ct} min</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Packing Cycle Time</span><span className="font-bold">{data.outbound.packing_ct} min</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Outbound Queue</span><span className="font-bold">{data.outbound.queue} units</span></div>
            <div className="flex justify-between p-2 bg-gray-50 rounded"><span>Outbound Utilization</span><span className="font-bold">{data.outbound.utilization}%</span></div>
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.outbound.chart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <Tooltip />
                <Area type="monotone" dataKey="throughput" stroke="#8b5cf6" fill="#ddd6fe" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* SECTION 4 - INVENTORY EFFICIENCY */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4">INVENTORY OPERATIONS</h2>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
          <div className="p-3 bg-gray-50 rounded"><p className="text-xs text-gray-500">Inventory Movement</p><p className="font-bold">{data.inventory.movement}</p></div>
          <div className="p-3 bg-gray-50 rounded"><p className="text-xs text-gray-500">Storage Utilization</p><p className="font-bold">{data.inventory.utilization}%</p></div>
          <div className="p-3 bg-gray-50 rounded"><p className="text-xs text-gray-500">Inbound Move</p><p className="font-bold text-blue-600">+{data.inventory.inbound}</p></div>
          <div className="p-3 bg-gray-50 rounded"><p className="text-xs text-gray-500">Outbound Move</p><p className="font-bold text-purple-600">-{data.inventory.outbound}</p></div>
          <div className="p-3 bg-gray-50 rounded"><p className="text-xs text-gray-500">Inventory Change</p><p className="font-bold text-red-500">{data.inventory.change}</p></div>
          <div className="p-3 bg-gray-50 rounded"><p className="text-xs text-gray-500">Trend</p><p className="font-bold">{data.inventory.trend}</p></div>
        </div>
      </div>

      {/* SECTION 10 - AI INSIGHTS */}
      <div className="bg-blue-50 p-6 rounded-xl border border-blue-200 shadow">
        <h2 className="text-xl font-bold mb-4 text-blue-900 flex items-center gap-2">
          <span>AI Performance Insights</span>
        </h2>
        <div className="space-y-4">
          <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-100">
            <p className="text-sm font-bold text-gray-700">OBSERVATION</p>
            <p className="text-gray-900 mt-1">{data.insights.observation}</p>
          </div>
          <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-100">
            <p className="text-sm font-bold text-gray-700">EVIDENCE</p>
            <p className="text-gray-900 mt-1">{data.insights.evidence}</p>
          </div>
          <div className="p-4 bg-white rounded-lg shadow-sm border border-gray-100">
            <p className="text-sm font-bold text-gray-700">POSSIBLE FACTORS</p>
            <p className="text-gray-900 mt-1">{data.insights.factors}</p>
          </div>
          <div className="p-4 bg-yellow-50 rounded-lg border-l-4 border-yellow-400">
            <p className="text-sm font-bold text-yellow-800">RECOMMENDATION</p>
            <p className="text-yellow-900 mt-1">{data.insights.recommendation}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
