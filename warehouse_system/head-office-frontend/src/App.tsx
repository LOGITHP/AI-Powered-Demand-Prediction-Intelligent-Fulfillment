import { useState, useEffect } from 'react'
import { Activity, AlertTriangle, CheckCircle, Clock, Zap, Map } from 'lucide-react'
import axios from 'axios'

interface NetworkState {
  total_warehouses: number
  overall_health: string
  active_alerts: number
  pending_decisions: number
}

function App() {
  const [networkState, setNetworkState] = useState<NetworkState | null>(null)
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        const stateRes = await axios.get('http://localhost:8001/network-state');
        setNetworkState(stateRes.data);
      } catch (e) {
        console.error('Failed to fetch network state', e);
        // Fallback
        setNetworkState({
          total_warehouses: 4,
          overall_health: 'GOOD',
          active_alerts: 2,
          pending_decisions: 1
        });
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [])

  const handleApprove = async (decisionId: string, approved: boolean) => {
    try {
      await axios.post('http://localhost:8001/approve', {
        decision_id: decisionId,
        approved: approved,
        reason: approved ? undefined : 'Manager declined the decision manually'
      });
      alert(approved ? 'Decision Approved & Executing' : 'Decision Declined');
      // Refresh state
      const stateRes = await axios.get('http://localhost:8001/network-state');
      setNetworkState(stateRes.data);
    } catch (e) {
      console.error('Failed to submit approval', e);
      alert('Failed to communicate with AI orchestrator');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-2">
              <Map className="w-6 h-6 text-indigo-600" />
              <span className="text-xl font-semibold">Head Office Orchestrator</span>
            </div>
            <div className="flex space-x-4">
              <span className="text-sm font-medium px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full">
                Network Status: {networkState?.overall_health}
              </span>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">Total Warehouses</p>
              <p className="text-2xl font-bold">{networkState?.total_warehouses || 0}</p>
            </div>
            <div className="bg-blue-50 p-3 rounded-lg">
              <Map className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">Active Alerts</p>
              <p className="text-2xl font-bold text-red-600">{networkState?.active_alerts || 0}</p>
            </div>
            <div className="bg-red-50 p-3 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">Pending Decisions</p>
              <p className="text-2xl font-bold text-amber-600">{networkState?.pending_decisions || 0}</p>
            </div>
            <div className="bg-amber-50 p-3 rounded-lg">
              <Activity className="w-6 h-6 text-amber-600" />
            </div>
          </div>
          
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">System Health</p>
              <p className="text-2xl font-bold text-green-600">{networkState?.overall_health || 'UNKNOWN'}</p>
            </div>
            <div className="bg-green-50 p-3 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                Network Alerts
              </h2>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="p-4 border border-red-100 bg-red-50 rounded-lg">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-semibold text-red-800">High Demand Spike - WH-NORTH</h3>
                      <p className="text-sm text-red-600 mt-1">Order volume exceeded capacity by 25%. Processing delays likely.</p>
                    </div>
                    <span className="text-xs text-red-500 font-medium">10 mins ago</span>
                  </div>
                  <div className="mt-3 flex gap-2">
                    <button className="text-xs px-3 py-1 bg-red-600 text-white rounded-md hover:bg-red-700">Re-route Orders</button>
                    <button className="text-xs px-3 py-1 bg-white border border-red-200 text-red-700 rounded-md hover:bg-red-50">Dismiss</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-500" />
                AI Orchestrator Decisions
              </h2>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-amber-100 text-amber-800 mb-2">
                        <Clock className="w-3 h-3" /> Pending Approval
                      </span>
                      <h3 className="font-semibold">Resource Reallocation</h3>
                      <p className="text-sm text-gray-600 mt-1">Move 5 workers from WH-EAST to WH-NORTH to handle demand spike.</p>
                      
                      <div className="mt-3 p-3 bg-gray-50 rounded text-sm text-gray-700">
                        <p className="font-medium mb-1 flex items-center gap-1"><Zap className="w-4 h-4 text-amber-500"/> AI Reasoning:</p>
                        <ul className="list-disc pl-5 space-y-1">
                          <li>WH-NORTH facing 25% order volume spike.</li>
                          <li>WH-EAST is operating at 60% capacity with surplus staff.</li>
                          <li>Distance between facilities allows same-day transfer.</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 flex gap-3 border-t border-gray-100 pt-4">
                    <button 
                      onClick={() => handleApprove('decision-123', true)}
                      className="flex-1 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700">
                      Approve & Execute
                    </button>
                    <button 
                      onClick={() => handleApprove('decision-123', false)}
                      className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">
                      Decline
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* --- New Visualization Section --- */}
        <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Map className="w-5 h-5 text-indigo-500" />
              Global Warehouse Load Visualization
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Bar Chart 1 */}
              <div className="space-y-4">
                <h3 className="font-medium text-gray-700">WH-NORTH Capacity</h3>
                <div className="w-full bg-gray-100 rounded-full h-4">
                  <div className="bg-red-500 h-4 rounded-full" style={{ width: '92%' }}></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Current: 92% (Overloaded)</span>
                  <span>100%</span>
                </div>
              </div>

              {/* Bar Chart 2 */}
              <div className="space-y-4">
                <h3 className="font-medium text-gray-700">WH-EAST Capacity</h3>
                <div className="w-full bg-gray-100 rounded-full h-4">
                  <div className="bg-green-500 h-4 rounded-full" style={{ width: '45%' }}></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Current: 45% (Available)</span>
                  <span>100%</span>
                </div>
              </div>

              {/* Bar Chart 3 */}
              <div className="space-y-4">
                <h3 className="font-medium text-gray-700">WH-SOUTH Capacity</h3>
                <div className="w-full bg-gray-100 rounded-full h-4">
                  <div className="bg-amber-500 h-4 rounded-full" style={{ width: '78%' }}></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Current: 78% (Busy)</span>
                  <span>100%</span>
                </div>
              </div>

            </div>
            
            <div className="mt-8 pt-6 border-t border-gray-100 grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <h3 className="font-medium text-gray-700 mb-4">Throughput Trend (Last 7 Days)</h3>
                <div className="flex items-end gap-2 h-32">
                  <div className="bg-indigo-200 hover:bg-indigo-400 w-full rounded-t-sm transition-colors" style={{ height: '40%' }}></div>
                  <div className="bg-indigo-300 hover:bg-indigo-500 w-full rounded-t-sm transition-colors" style={{ height: '55%' }}></div>
                  <div className="bg-indigo-300 hover:bg-indigo-500 w-full rounded-t-sm transition-colors" style={{ height: '50%' }}></div>
                  <div className="bg-indigo-400 hover:bg-indigo-600 w-full rounded-t-sm transition-colors" style={{ height: '65%' }}></div>
                  <div className="bg-indigo-500 hover:bg-indigo-700 w-full rounded-t-sm transition-colors" style={{ height: '80%' }}></div>
                  <div className="bg-indigo-600 hover:bg-indigo-800 w-full rounded-t-sm transition-colors" style={{ height: '70%' }}></div>
                  <div className="bg-indigo-700 hover:bg-indigo-900 w-full rounded-t-sm transition-colors" style={{ height: '95%' }}></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-2">
                  <span>Mon</span>
                  <span>Tue</span>
                  <span>Wed</span>
                  <span>Thu</span>
                  <span>Fri</span>
                  <span>Sat</span>
                  <span>Sun</span>
                </div>
              </div>
              
              <div className="bg-slate-50 p-4 rounded-lg border border-gray-100 flex flex-col justify-center">
                <h3 className="font-semibold text-gray-800 mb-2">Automated Network Report</h3>
                <p className="text-sm text-gray-600 mb-4">
                  The AI Agent has analyzed global processing loads. WH-NORTH is critically overloaded due to an unexpected shipment surge. 
                  Re-routing new standard deliveries to WH-EAST is highly recommended to balance the network.
                </p>
                <button className="self-start text-sm text-indigo-600 font-medium hover:underline flex items-center gap-1">
                  View Full Analytics Report &rarr;
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
