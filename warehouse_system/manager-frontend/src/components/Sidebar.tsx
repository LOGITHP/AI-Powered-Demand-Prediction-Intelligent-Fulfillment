import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  PackageSearch, 
  Users, 
  Settings,
  LogOut,
  BrainCircuit,
  MessageSquareWarning
} from 'lucide-react';

export default function Sidebar() {
  const location = useLocation();
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Operations', path: '/operations', icon: PackageSearch },
    { name: 'Workforce', path: '/workforce', icon: Users },
    { name: 'AI Agent', path: '/agent', icon: BrainCircuit },
    { name: 'Alerts', path: '/alerts', icon: MessageSquareWarning },
  ];

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    window.location.href = '/login';
  };

  return (
    <div className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
      <div className="p-6">
        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
          Warehouse AI
        </h1>
        <p className="text-xs text-slate-400 mt-1">Manager Portal</p>
      </div>
      
      <nav className="flex-1 px-4 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.name}
            to={item.path}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
              location.pathname === item.path 
                ? 'bg-blue-600/20 text-blue-400 font-medium' 
                : 'text-slate-400 hover:bg-slate-700/50 hover:text-slate-200'
            }`}
          >
            <item.icon size={20} />
            {item.name}
          </Link>
        ))}
      </nav>
      
      <div className="p-4 border-t border-slate-700">
        <button onClick={handleLogout} className="flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-red-400 transition-colors w-full">
          <LogOut size={20} />
          Logout
        </button>
      </div>
    </div>
  );
}
