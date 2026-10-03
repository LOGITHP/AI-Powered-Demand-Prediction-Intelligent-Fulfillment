import { Package, Users, ShoppingCart, AlertTriangle, ArrowUpRight, ArrowDownRight, Clock, Activity, Box, MoreHorizontal, Brain } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { fetchDashboardMetrics } from '../../services/dashboardApi';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboardMetrics'],
    queryFn: fetchDashboardMetrics,
  });

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 h-full flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mb-4">
          <AlertTriangle size={32} />
        </div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Failed to load metrics</h2>
        <p className="text-slate-500 mb-4">We couldn't connect to the backend API. Ensure the server is running.</p>
        <button 
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  const metrics = data;

  const workforceData = [
    { name: 'Present', value: metrics?.presentWorkers || 0, color: '#2563eb' },
    { name: 'Absent', value: 50 - (metrics?.presentWorkers || 0), color: '#e2e8f0' }
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Warehouse Operations</h1>
          <p className="text-slate-500 mt-1 font-medium">Real-time operational overview for WH-001</p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-semibold hover:bg-slate-50 transition-colors shadow-sm">
            Export Report
          </button>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm shadow-blue-600/20">
            Generate AI Insights
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <KpiCard title="Orders Today" value={metrics?.ordersToday} icon={<ShoppingCart size={22} />} trend="+12%" positive={true} color="blue" />
        <KpiCard title="Pending Orders" value={metrics?.pendingOrders} icon={<Clock size={22} />} color="amber" />
        <KpiCard title="Inbound Shipments" value={metrics?.inboundShipments} icon={<Package size={22} />} color="indigo" />
        <KpiCard title="Warehouse Util." value={`${metrics?.utilizationPercent || 0}%`} icon={<Activity size={22} />} status={(metrics?.utilizationPercent || 0) > 85 ? 'HIGH' : 'NORMAL'} color="emerald" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Workforce Status */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 col-span-1 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Users size={20} className="text-blue-600"/> Workforce Status
            </h2>
            <button className="text-slate-400 hover:text-slate-600"><MoreHorizontal size={20} /></button>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="h-36 w-36 relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={workforceData}
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={65}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                    cornerRadius={4}
                  >
                    {workforceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    itemStyle={{ fontWeight: 600 }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-extrabold text-slate-900">50</span>
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Total</span>
              </div>
            </div>
            
            <div className="flex flex-col gap-3 flex-1">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-600 font-medium flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-blue-600 shadow-sm shadow-blue-600/30"></div> Present</span>
                <span className="font-bold text-slate-900">{metrics?.presentWorkers || 0}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-600 font-medium flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-slate-200"></div> Absent</span>
                <span className="font-bold text-slate-900">{50 - (metrics?.presentWorkers || 0)}</span>
              </div>
            </div>
          </div>

          <div className="mt-8 bg-slate-50 p-4 rounded-xl border border-slate-100">
            <div className="flex justify-between text-xs font-bold mb-2 text-slate-500 uppercase tracking-wider">
              <span>Required: {metrics?.requiredWorkers || 0}</span>
              <span className="text-blue-600">Available: {metrics?.presentWorkers || 0}</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden flex shadow-inner">
              <div className="bg-blue-600 h-full rounded-full transition-all duration-500" style={{ width: `${(metrics?.presentWorkers || 0) / (metrics?.requiredWorkers || 1) * 100}%` }}></div>
            </div>
            {(metrics?.presentWorkers || 0) < (metrics?.requiredWorkers || 0) && (
              <div className="mt-3 text-xs text-rose-600 flex items-center justify-center gap-1.5 font-bold bg-rose-50 border border-rose-100 px-3 py-2 rounded-lg">
                <AlertTriangle size={14} /> Shortage of {(metrics?.requiredWorkers || 0) - (metrics?.presentWorkers || 0)} workers
              </div>
            )}
          </div>
        </div>

        {/* Live Warehouse Workflow */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 col-span-2 flex flex-col">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Activity size={20} className="text-indigo-600"/> Live Workflow & Pipeline
            </h2>
            <span className="text-xs font-bold bg-emerald-50 text-emerald-600 px-2 py-1 rounded-md border border-emerald-100 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Live Sync
            </span>
          </div>
          
          <div className="flex items-center justify-between mt-6 relative flex-1">
            {/* Connecting Line */}
            <div className="absolute top-[22px] left-8 right-8 h-1 bg-slate-100 -z-10 rounded-full"></div>
            
            <WorkflowStage name="Receiving" tasks={12} workers={3} util={70} color="indigo" />
            <WorkflowStage name="Quality" tasks={5} workers={2} util={45} color="blue" />
            <WorkflowStage name="Put-Away" tasks={18} workers={5} util={85} color="sky" />
            <WorkflowStage name="Picking" tasks={46} workers={10} util={92} active={true} delay={true} color="violet" />
            <WorkflowStage name="Packing" tasks={28} workers={4} util={88} color="fuchsia" />
            <WorkflowStage name="Dispatch" tasks={15} workers={3} util={60} color="rose" />
          </div>
          
          <div className="mt-8 bg-indigo-50/50 border border-indigo-100 rounded-xl p-4 flex items-center gap-4">
            <div className="bg-indigo-100 p-2 rounded-lg text-indigo-600">
              <Brain size={20} />
            </div>
            <div>
              <h4 className="text-sm font-bold text-indigo-900">AI Recommendation</h4>
              <p className="text-xs text-indigo-700 mt-0.5 font-medium">Reallocate 2 workers from 'Quality' to 'Picking' to clear the current bottleneck.</p>
            </div>
            <button className="ml-auto px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow-sm transition-colors">
              Apply Fix
            </button>
          </div>
        </div>
      </div>

    </div>
  );
}

const colorMap: Record<string, string> = {
  blue: 'bg-blue-50 text-blue-600 border-blue-100',
  amber: 'bg-amber-50 text-amber-600 border-amber-100',
  indigo: 'bg-indigo-50 text-indigo-600 border-indigo-100',
  emerald: 'bg-emerald-50 text-emerald-600 border-emerald-100',
};

function KpiCard({ title, value, icon, trend, positive, status, color = 'blue' }: any) {
  const colorClasses = colorMap[color];
  
  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col group hover:shadow-md transition-shadow cursor-pointer">
      <div className="flex justify-between items-start mb-6">
        <div className={`p-2.5 rounded-xl border ${colorClasses}`}>
          {icon}
        </div>
        {status && (
          <span className={`text-[10px] font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wider ${status === 'HIGH' ? 'bg-amber-100 text-amber-700 border border-amber-200' : 'bg-emerald-100 text-emerald-700 border border-emerald-200'}`}>
            {status}
          </span>
        )}
      </div>
      <div className="flex flex-col">
        <span className="text-3xl font-extrabold text-slate-900 mb-1">{value || '-'}</span>
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">{title}</span>
          {trend && (
            <span className={`text-xs font-bold flex items-center gap-0.5 px-1.5 py-0.5 rounded-md ${positive ? 'text-emerald-600 bg-emerald-50' : 'text-rose-600 bg-rose-50'}`}>
              {positive ? <ArrowUpRight size={14}/> : <ArrowDownRight size={14}/>} {trend}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function WorkflowStage({ name, tasks, workers, util, active, delay }: any) {
  return (
    <div className="flex flex-col items-center group relative cursor-pointer flex-1">
      <div className={`w-12 h-12 rounded-full flex items-center justify-center border-4 z-10 transition-all shadow-sm ${
        active 
          ? 'bg-violet-600 border-violet-100 text-white scale-110 ring-4 ring-violet-600/20' 
          : 'bg-white border-slate-200 text-slate-400 group-hover:border-blue-300 group-hover:text-blue-500'
      }`}>
        <Box size={active ? 20 : 18} className={active ? '' : 'opacity-70'} />
      </div>
      
      {delay && (
        <div className="absolute top-0 right-1/4 translate-x-2 -translate-y-1 w-5 h-5 bg-rose-500 rounded-full text-white flex items-center justify-center border-2 border-white z-20 shadow-sm" title="Delayed tasks">
          <span className="text-xs font-bold">!</span>
        </div>
      )}
      
      <div className="mt-4 text-center">
        <div className={`text-xs font-extrabold mb-0.5 ${active ? 'text-violet-700' : 'text-slate-700'}`}>{name}</div>
        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
          {tasks} Tasks
        </div>
      </div>
      
      {/* Tooltip on hover */}
      <div className="absolute top-16 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800 text-white text-xs rounded-lg p-3 z-30 w-36 shadow-xl pointer-events-none -translate-x-1/2 left-1/2">
        <div className="font-bold border-b border-slate-700 pb-2 mb-2 text-center text-slate-200">{name} Stage</div>
        <div className="flex justify-between mb-1.5"><span className="text-slate-400 font-medium">Workers:</span> <span className="font-bold">{workers}</span></div>
        <div className="flex justify-between mb-1.5"><span className="text-slate-400 font-medium">Util:</span> <span className={`font-bold ${util > 90 ? 'text-amber-400' : 'text-emerald-400'}`}>{util}%</span></div>
        {delay && <div className="flex justify-between text-rose-400 pt-1 border-t border-slate-700 mt-1"><span className="font-medium">Delayed:</span> <span className="font-bold">2 orders</span></div>}
      </div>
    </div>
  );
}
