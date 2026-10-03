import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../lib/api';

export default function Optimization() {
  const [data, setData] = useState<any>(null);
  const [scenario, setScenario] = useState('0');
  const [isApproved, setIsApproved] = useState(false);

  useEffect(() => {
    api.get('/ps/optimization').then(res => setData(res.data)).catch(console.error);
  }, []);

  if (!data) return <div className="p-8">Loading optimization data...</div>;

  const handleScenarioChange = (e: any) => {
    setScenario(e.target.value);
    api.get(`/ps/optimization?scenario=${e.target.value}`).then(res => setData(res.data)).catch(console.error);
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto text-gray-900">
      <h1 className="text-3xl font-bold">Resource Optimization Engine</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* SECTION 1 - UNDERUTILIZED */}
        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-bold mb-4 text-blue-900">UNDERUTILIZED OPERATIONAL AREAS</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-50">
                <tr>
                  <th className="p-2 text-sm font-semibold">Area</th>
                  <th className="p-2 text-sm font-semibold">Workload</th>
                  <th className="p-2 text-sm font-semibold">Capacity</th>
                  <th className="p-2 text-sm font-semibold">Utilization</th>
                  <th className="p-2 text-sm font-semibold">Potential Surplus</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.underutilized.map((u: any, i: number) => (
                  <tr key={i}>
                    <td className="p-2 font-medium">{u.area}</td>
                    <td className="p-2">{u.workload}</td>
                    <td className="p-2">{u.capacity}</td>
                    <td className="p-2 text-orange-600">{u.utilization}%</td>
                    <td className="p-2 text-green-600 font-bold">{u.surplus} workers</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* SECTION 2 - OVERUTILIZED */}
        <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-bold mb-4 text-red-900">OVERUTILIZED OPERATIONAL AREAS</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-50">
                <tr>
                  <th className="p-2 text-sm font-semibold">Area</th>
                  <th className="p-2 text-sm font-semibold">Workload</th>
                  <th className="p-2 text-sm font-semibold">Capacity</th>
                  <th className="p-2 text-sm font-semibold">Shortage</th>
                  <th className="p-2 text-sm font-semibold">Delay Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.overutilized.map((o: any, i: number) => (
                  <tr key={i}>
                    <td className="p-2 font-medium">{o.area}</td>
                    <td className="p-2">{o.workload}</td>
                    <td className="p-2">{o.capacity}</td>
                    <td className="p-2 text-red-600 font-bold">{o.shortage} workers</td>
                    <td className="p-2 text-red-600 font-bold">{o.risk}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* SECTION 3 - REDISTRIBUTION */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4">WORKFORCE REDISTRIBUTION RECOMMENDATION</h2>
        <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 flex items-center justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-4">
              <span className="font-bold text-lg">{data.redistribution.source}</span>
              <span className="text-gray-400">→</span>
              <span className="font-bold text-lg">{data.redistribution.destination}</span>
            </div>
            <p className="text-blue-600 font-bold">{data.redistribution.workers} workers</p>
            <p className="text-sm text-gray-600">Reason: {data.redistribution.reason}</p>
            <p className={`text-sm font-bold ${isApproved ? 'text-green-600' : 'text-yellow-600'}`}>
              Status: {isApproved ? 'Approved & Dispatched' : data.redistribution.status}
            </p>
          </div>
          <button 
            onClick={async () => {
              setIsApproved(true);
              try {
                await api.post('/ps/optimization/approve');
                alert("Redistribution approved! Workforce task dispatched to the terminals.");
              } catch (err) {
                console.error(err);
                alert("Failed to notify workers.");
              }
            }}
            disabled={isApproved}
            className={`${isApproved ? 'bg-green-600 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'} text-white px-6 py-3 rounded-lg font-medium shadow-sm transition-colors`}
          >
            {isApproved ? 'Approved' : 'Approve Redistribution'}
          </button>
        </div>
      </div>

      {/* SECTION 4 - LABOUR PLANNING ACCURACY */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4">LABOUR PLANNING ACCURACY</h2>
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="p-4 bg-gray-50 rounded"><p className="text-sm text-gray-500">Predicted Workers</p><p className="text-xl font-bold">{data.accuracy.predicted}</p></div>
          <div className="p-4 bg-gray-50 rounded"><p className="text-sm text-gray-500">Actual Workers</p><p className="text-xl font-bold">{data.accuracy.actual}</p></div>
          <div className="p-4 bg-gray-50 rounded"><p className="text-sm text-gray-500">Prediction Error</p><p className="text-xl font-bold">{data.accuracy.error}</p></div>
          <div className="p-4 bg-green-50 rounded"><p className="text-sm text-gray-500">Planning Accuracy</p><p className="text-xl font-bold text-green-700">{data.accuracy.pct}%</p></div>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.accuracy.chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="predicted" stroke="#3b82f6" name="Predicted Requirement" />
              <Line type="monotone" dataKey="actual" stroke="#10b981" name="Actual Usage" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SECTION 5 & 6 - SCENARIO PLANNING */}
      <div className="bg-white p-6 rounded-xl shadow border border-gray-200">
        <h2 className="text-xl font-bold mb-4">SCENARIO PLANNING (PEAK / NON-PEAK)</h2>
        <div className="mb-6 flex items-center gap-4">
          <label className="font-medium">Simulate Workload Change:</label>
          <select value={scenario} onChange={handleScenarioChange} className="border border-gray-300 rounded px-3 py-2 bg-gray-50">
            <option value="0">Current State (0%)</option>
            <option value="10">+10% (Peak)</option>
            <option value="20">+20% (Peak)</option>
            <option value="30">+30% (Peak)</option>
            <option value="-10">-10% (Non-Peak)</option>
            <option value="-20">-20% (Non-Peak)</option>
            <option value="-30">-30% (Non-Peak)</option>
          </select>
          <span className="text-sm text-gray-500 ml-4">* Scenario simulation does NOT modify real warehouse data</span>
        </div>

        <div className="grid grid-cols-2 gap-8">
          <div className="p-4 border border-gray-200 rounded-xl bg-gray-50">
            <h3 className="font-bold mb-4 text-gray-500">CURRENT STATE</h3>
            <div className="space-y-2">
              <div className="flex justify-between"><span>Workload:</span> <b>{data.scenario.current.workload} units</b></div>
              <div className="flex justify-between"><span>Required Workers:</span> <b>{data.scenario.current.workers}</b></div>
              <div className="flex justify-between"><span>Available Workers:</span> <b>{data.scenario.current.available}</b></div>
              <div className="flex justify-between"><span>Processing Time:</span> <b>{data.scenario.current.time} min</b></div>
            </div>
          </div>
          <div className="p-4 border border-blue-200 rounded-xl bg-blue-50">
            <h3 className="font-bold mb-4 text-blue-800">SCENARIO SIMULATION</h3>
            <div className="space-y-2">
              <div className="flex justify-between"><span>Projected Workload:</span> <b>{data.scenario.simulated.workload} units</b></div>
              <div className="flex justify-between"><span>Required Workers:</span> <b>{data.scenario.simulated.workers}</b></div>
              <div className="flex justify-between">
                <span>Worker Shortage/Surplus:</span> 
                <b className={data.scenario.simulated.diff < 0 ? "text-red-600" : "text-green-600"}>{data.scenario.simulated.diff}</b>
              </div>
              <div className="flex justify-between"><span>Processing Time:</span> <b>{data.scenario.simulated.time} min</b></div>
              <div className="flex justify-between"><span>Delay Risk:</span> <b className="text-red-600">{data.scenario.simulated.risk}%</b></div>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
