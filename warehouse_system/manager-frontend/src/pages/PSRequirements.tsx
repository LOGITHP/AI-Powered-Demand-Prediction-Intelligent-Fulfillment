import { CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function PSRequirements() {
  const sections = [
    {
      title: "VOLUME FORECASTING",
      link: "/forecasting",
      items: [
        "Inbound shipment volume prediction",
        "Outbound order volume forecasting",
        "Inventory movement trend estimation",
        "Workload projection"
      ]
    },
    {
      title: "SMART WORKFORCE PLANNING",
      link: "/workforce",
      items: [
        "Automatic manpower calculation",
        "Optimal staffing recommendation",
        "Shift planning",
        "Workforce allocation",
        "Resource-demand matching"
      ]
    },
    {
      title: "OPERATIONS EFFICIENCY DASHBOARD",
      link: "/analytics",
      items: [
        "Operational KPIs",
        "Benchmarks",
        "Inbound efficiency",
        "Outbound efficiency",
        "Inventory efficiency",
        "Throughput",
        "Cycle time",
        "Utilization",
        "Trend analysis",
        "Performance insights"
      ]
    },
    {
      title: "RESOURCE OPTIMIZATION",
      link: "/optimization",
      items: [
        "Underutilized area detection",
        "Overutilized area detection",
        "Workforce redistribution",
        "Labour planning accuracy",
        "Peak scenario planning",
        "Non-peak scenario planning"
      ]
    }
  ];

  return (
    <div className="space-y-8 max-w-4xl mx-auto text-gray-900 min-h-screen">
      <h1 className="text-3xl font-bold mb-8">PS Requirement Coverage</h1>
      
      <div className="grid gap-6">
        {sections.map(section => (
          <div key={section.title} className="bg-white border border-gray-200 shadow rounded-xl p-6 hover:shadow-md transition-shadow">
            <Link to={section.link} className="block group">
              <h2 className="text-xl font-bold text-blue-900 group-hover:text-blue-600 transition-colors flex items-center justify-between">
                {section.title}
                <span className="text-sm font-normal text-gray-500 group-hover:text-blue-500">View Page →</span>
              </h2>
            </Link>
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
              {section.items.map(item => (
                <div key={item} className="flex items-center gap-2">
                  <CheckCircle2 size={18} className="text-green-500 shrink-0" />
                  <span className="text-gray-700">{item}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
