import { useState, useEffect } from 'react';
import { Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Line } from 'recharts';
import api from '../lib/api';

export default function Workforce() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.get('/ps/workforce').then(res => setData(res.data)).catch(console.error);
  }, []);

  const [selectedShift, setSelectedShift] = useState<string>('All');

  if (!data) return <div className="p-8">Loading workforce data...</div>;

  const filteredShifts = data.shifts.filter((w: any) => selectedShift === 'All' || w.shift === selectedShift);

  return (
    <div className="space-y-8 max-w-6xl mx-auto text-gray-900">
      <h1 className="text-3xl font-bold">Smart Workforce Planning</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* SECTION 1 */}
        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-bold mb-4 text-blue-900">AUTOMATIC MANPOWER REQUIREMENT</h2>
          <p className="text-sm text-gray-500 mb-4">ML Predicted Labour Requirement</p>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded"><span>REQUIRED WORKERS</span><span className="font-bold text-lg">{data.manpower.required}</span></div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded"><span>AVAILABLE WORKERS</span><span className="font-bold text-lg">{data.manpower.available}</span></div>
            <div className="flex justify-between items-center p-3 bg-red-50 text-red-700 rounded"><span>WORKER SHORTAGE</span><span className="font-bold text-lg">{data.manpower.shortage}</span></div>
            <div className="flex justify-between items-center p-3 bg-green-50 text-green-700 rounded"><span>WORKER SURPLUS</span><span className="font-bold text-lg">{data.manpower.surplus}</span></div>
          </div>
        </div>

        {/* SECTION 2 */}
        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-bold mb-4 text-green-900">RECOMMENDED STAFFING LEVEL</h2>
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg mb-6">
            <p className="text-blue-800 font-bold text-lg">Recommended Workers: {data.recommendation.recommended}</p>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="p-3 bg-gray-50 rounded"><p className="text-xs text-gray-500">Current</p><p className="font-bold text-xl">{data.recommendation.current}</p></div>
            <div className="p-3 bg-gray-50 rounded"><p className="text-xs text-gray-500">Required</p><p className="font-bold text-xl">{data.recommendation.required}</p></div>
            <div className="p-3 bg-red-50 rounded"><p className="text-xs text-gray-500">Gap</p><p className="font-bold text-xl text-red-600">{data.recommendation.gap}</p></div>
          </div>
          <div className="p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded">
            <p className="text-sm font-medium">Recommendation:</p>
            <p className="text-yellow-800 mt-1">{data.recommendation.action}</p>
          </div>
        </div>
      </div>

      {/* SECTION 3 */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4 text-purple-900">SHIFT PLANNING</h2>
        <div className="flex gap-2 mb-4">
          {['All', 'Morning', 'Afternoon', 'Night'].map(shift => (
            <button 
              key={shift} 
              onClick={() => setSelectedShift(shift)}
              className={`px-4 py-2 rounded font-medium text-sm transition-colors ${
                selectedShift === shift ? 'bg-purple-600 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
              }`}
            >
              {shift}
            </button>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-gray-50">
              <tr>
                <th className="p-3 text-sm font-semibold">Worker</th>
                <th className="p-3 text-sm font-semibold">Shift</th>
                <th className="p-3 text-sm font-semibold">Zone</th>
                <th className="p-3 text-sm font-semibold">Skill</th>
                <th className="p-3 text-sm font-semibold">Status</th>
                <th className="p-3 text-sm font-semibold">Current Assignment</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredShifts.map((w: any, i: number) => (
                <tr key={i}>
                  <td className="p-3">{w.worker}</td>
                  <td className="p-3">{w.shift}</td>
                  <td className="p-3">{w.zone}</td>
                  <td className="p-3">{w.skill}</td>
                  <td className="p-3">
                    <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">{w.status}</span>
                  </td>
                  <td className="p-3">{w.assignment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 4 */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4 text-orange-900">WORKFORCE ALLOCATION</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-gray-50">
              <tr>
                <th className="p-3 text-sm font-semibold">PROCESS</th>
                <th className="p-3 text-sm font-semibold">REQUIRED</th>
                <th className="p-3 text-sm font-semibold">AVAILABLE</th>
                <th className="p-3 text-sm font-semibold">SHORTAGE/SURPLUS</th>
                <th className="p-3 text-sm font-semibold">UTILIZATION</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.allocation.map((a: any, i: number) => (
                <tr key={i}>
                  <td className="p-3 font-medium">{a.process}</td>
                  <td className="p-3">{a.required}</td>
                  <td className="p-3">{a.available}</td>
                  <td className="p-3">
                    <span className={"px-2 py-1 rounded text-xs font-bold " + (a.diff < 0 ? "bg-red-100 text-red-700" : (a.diff > 0 ? "bg-blue-100 text-blue-700" : "bg-green-100 text-green-700"))}>
                      {a.diff < 0 ? a.diff : '+'+a.diff}
                    </span>
                  </td>
                  <td className="p-3">
                    <span className={"px-2 py-1 rounded text-xs font-bold " + (a.status === 'UNDERSTAFFED' ? "bg-red-100 text-red-700" : (a.status === 'OVERSTAFFED' ? "bg-blue-100 text-blue-700" : "bg-green-100 text-green-700"))}>
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 5 */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4">RESOURCE VS FORECASTED DEMAND</h2>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data.demand_chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis yAxisId="left" orientation="left" stroke="#8884d8" />
              <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="workload" fill="#8884d8" name="Forecasted Workload" />
              <Line yAxisId="right" type="monotone" dataKey="capacity" stroke="#82ca9d" name="Available Capacity" strokeWidth={3} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
