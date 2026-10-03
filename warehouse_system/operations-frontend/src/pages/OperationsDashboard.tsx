import { useState } from 'react';
import { PackageSearch, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';

export default function OperationsDashboard() {
  const [activeTask, setActiveTask] = useState<any>(null);

  const getTask = () => {
    setActiveTask({
      id: 'TASK-8472',
      type: 'PICKING',
      location: 'Aisle 12, Shelf B',
      items: 14,
      priority: 'HIGH'
    });
  };

  const completeTask = () => {
    setActiveTask(null);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      
      {!activeTask ? (
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-8 text-center">
          <div className="mx-auto w-20 h-20 bg-blue-500/20 rounded-full flex items-center justify-center mb-4">
            <PackageSearch size={40} className="text-blue-400" />
          </div>
          <h2 className="text-2xl font-bold mb-2">Ready for Assignment</h2>
          <p className="text-slate-400 mb-8">You currently have no active tasks.</p>
          
          <button 
            onClick={getTask}
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-xl text-lg font-medium transition-colors"
          >
            Get Next Task
          </button>
        </div>
      ) : (
        <div className="bg-slate-800 border border-blue-500/50 rounded-2xl overflow-hidden shadow-[0_0_15px_rgba(59,130,246,0.1)]">
          <div className="bg-blue-600/20 border-b border-blue-500/30 p-6 flex justify-between items-center">
            <div>
              <span className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded mb-2 inline-block">
                {activeTask.priority} PRIORITY
              </span>
              <h2 className="text-2xl font-bold text-blue-400">{activeTask.id}</h2>
              <p className="text-slate-300">{activeTask.type}</p>
            </div>
            <div className="text-right">
              <p className="text-slate-400 text-sm">Target Time</p>
              <p className="text-xl font-bold font-mono">14:30</p>
            </div>
          </div>
          
          <div className="p-6 grid grid-cols-2 gap-6">
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-700">
              <p className="text-sm text-slate-400 mb-1">Location</p>
              <p className="text-2xl font-bold">{activeTask.location}</p>
            </div>
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-700">
              <p className="text-sm text-slate-400 mb-1">Items to Pick</p>
              <p className="text-2xl font-bold">{activeTask.items}</p>
            </div>
          </div>
          
          <div className="p-6 pt-0 flex gap-4">
            <button className="flex-1 bg-slate-700 hover:bg-slate-600 px-4 py-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors">
              <AlertTriangle size={20} className="text-yellow-400" />
              Report Issue
            </button>
            <button 
              onClick={completeTask}
              className="flex-[2] bg-green-600 hover:bg-green-700 px-4 py-4 rounded-xl font-medium flex items-center justify-center gap-2 text-lg transition-colors shadow-lg"
            >
              <CheckCircle2 size={24} />
              Confirm Complete
            </button>
          </div>
        </div>
      )}
      
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
            <CheckCircle2 size={24} className="text-blue-400" />
          </div>
          <div>
            <p className="text-3xl font-bold">142</p>
            <p className="text-slate-400 text-sm">Tasks Completed Today</p>
          </div>
        </div>
        <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
            <Clock size={24} className="text-purple-400" />
          </div>
          <div>
            <p className="text-3xl font-bold">4.2m</p>
            <p className="text-slate-400 text-sm">Avg Task Time</p>
          </div>
        </div>
      </div>
    </div>
  );
}
