import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';

export default function Alerts() {
  return (
    <div className="space-y-8 max-w-5xl">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Network Alerts</h1>
      </div>

      <div className="space-y-4">
        {/* High Priority Alert */}
        <div className="bg-white rounded-xl shadow-sm border-l-4 border-l-red-500 overflow-hidden">
          <div className="p-5 flex items-start gap-4">
            <div className="p-2 bg-red-50 rounded-full text-red-600 mt-1">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-gray-900">Capacity Critical: WH-NORTH</h3>
                <span className="text-xs font-semibold text-gray-500">10 mins ago</span>
              </div>
              <p className="text-gray-600 mt-1 text-sm">
                Warehouse NORTH has exceeded 90% capacity utilization. Inbound shipments will be delayed if no action is taken.
              </p>
              <div className="mt-3 flex gap-2">
                <button className="text-sm font-semibold text-indigo-600 hover:text-indigo-800">View Details</button>
                <button className="text-sm font-semibold text-gray-500 hover:text-gray-700">Dismiss</button>
              </div>
            </div>
          </div>
        </div>

        {/* Medium Priority Alert */}
        <div className="bg-white rounded-xl shadow-sm border-l-4 border-l-amber-500 overflow-hidden">
          <div className="p-5 flex items-start gap-4">
            <div className="p-2 bg-amber-50 rounded-full text-amber-600 mt-1">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-gray-900">Worker Shortage: WH-SOUTH</h3>
                <span className="text-xs font-semibold text-gray-500">1 hour ago</span>
              </div>
              <p className="text-gray-600 mt-1 text-sm">
                Predicted afternoon peak requires 5 additional workers to meet SLAs for outbound orders.
              </p>
              <div className="mt-3 flex gap-2">
                <button className="text-sm font-semibold text-indigo-600 hover:text-indigo-800">View Details</button>
                <button className="text-sm font-semibold text-gray-500 hover:text-gray-700">Dismiss</button>
              </div>
            </div>
          </div>
        </div>

        {/* Low Priority / Info */}
        <div className="bg-white rounded-xl shadow-sm border-l-4 border-l-blue-500 overflow-hidden">
          <div className="p-5 flex items-start gap-4">
            <div className="p-2 bg-blue-50 rounded-full text-blue-600 mt-1">
              <Info className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-gray-900">System Maintenance Scheduled</h3>
                <span className="text-xs font-semibold text-gray-500">5 hours ago</span>
              </div>
              <p className="text-gray-600 mt-1 text-sm">
                Global routing orchestrator will be offline for 10 minutes on Sunday at 2 AM EST.
              </p>
              <div className="mt-3 flex gap-2">
                <button className="text-sm font-semibold text-indigo-600 hover:text-indigo-800">View Details</button>
                <button className="text-sm font-semibold text-gray-500 hover:text-gray-700">Dismiss</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
