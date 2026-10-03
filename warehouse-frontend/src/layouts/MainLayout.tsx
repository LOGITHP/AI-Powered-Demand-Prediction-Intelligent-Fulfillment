import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Package, ArrowDownToLine, ArrowUpFromLine, ShoppingCart, Users, UserCheck, ClipboardList, Activity, Brain, Bell, ListTodo, Search, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

function LogoutButton() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <button 
      onClick={handleLogout}
      className="text-slate-500 hover:text-rose-600 p-2 rounded-full hover:bg-rose-50 transition-colors"
      title="Logout"
    >
      <LogOut size={20} />
    </button>
  );
}

export default function MainLayout() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-slate-200 flex flex-col h-full shrink-0 shadow-sm z-10">
        <div className="p-5 flex items-center border-b border-slate-100">
          <div className="text-2xl font-extrabold tracking-tight text-blue-600">main <span className="text-slate-800">branch</span></div>
        </div>
        <div className="px-5 py-3 bg-blue-50/50 border-b border-blue-100">
          <div className="text-[10px] text-blue-600 font-bold uppercase tracking-widest mb-0.5">Active Warehouse</div>
          <div className="text-sm font-bold text-slate-800 flex items-center justify-between">
            WH-001
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-0.5">
          <div className="px-5 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-2">Overview</div>
          <NavItem to="/dashboard" icon={<LayoutDashboard size={18} />} label="Dashboard" />
          
          <div className="px-5 pt-4 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Operations</div>
          <NavItem to="/inbound" icon={<ArrowDownToLine size={18} />} label="Inbound" />
          <NavItem to="/outbound" icon={<ArrowUpFromLine size={18} />} label="Outbound" />
          <NavItem to="/orders" icon={<ShoppingCart size={18} />} label="Orders" />
          <NavItem to="/inventory" icon={<Package size={18} />} label="Inventory" />
          
          <div className="px-5 pt-4 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Workforce</div>
          <NavItem to="/workers" icon={<Users size={18} />} label="Workers" />
          <NavItem to="/attendance" icon={<UserCheck size={18} />} label="Attendance" />
          <NavItem to="/tasks" icon={<ClipboardList size={18} />} label="Task Allocation" />
          
          <div className="px-5 pt-4 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">AI Intelligence</div>
          <NavItem to="/predictions" icon={<Activity size={18} />} label="Predictions" />
          <NavItem to="/recommendations" icon={<Brain size={18} />} label="Recommendations" />
          
          <div className="px-5 pt-4 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">Monitoring</div>
          <NavItem to="/alerts" icon={<Bell size={18} />} label="Alerts" />
          <NavItem to="/activity" icon={<ListTodo size={18} />} label="Activity" />
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0 z-0">
          <div className="flex items-center gap-6 flex-1">
            <div className="relative w-96 hidden md:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input 
                type="text" 
                placeholder="Search orders, inventory, or workers..." 
                className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800 placeholder-slate-400"
              />
            </div>
          </div>
          <div className="flex items-center gap-5">
            <div className="text-sm font-medium text-slate-600 hidden sm:block">
              Shift: <span className="text-blue-600 font-bold bg-blue-50 px-2 py-1 rounded-md">Morning</span>
            </div>
            <div className="h-6 w-px bg-slate-200"></div>
            <button className="relative p-2 text-slate-400 hover:text-blue-600 transition-colors rounded-full hover:bg-slate-50">
              <Bell size={20} />
              <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-rose-500 border-2 border-white rounded-full"></span>
            </button>
            <div className="h-9 w-9 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-sm ring-2 ring-white cursor-pointer hover:opacity-90 transition-opacity">
              M
            </div>
            <LogoutButton />
          </div>
        </header>
        <main className="flex-1 overflow-auto bg-slate-50">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function NavItem({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink 
      to={to} 
      className={({ isActive }) => 
        `flex items-center gap-3 px-5 py-2.5 text-sm font-medium transition-all mx-2 rounded-lg ${
          isActive 
            ? 'bg-blue-50 text-blue-700 shadow-sm ring-1 ring-blue-100/50' 
            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <div className={isActive ? 'text-blue-600' : 'text-slate-400'}>
            {icon}
          </div>
          <span>{label}</span>
        </>
      )}
    </NavLink>
  );
}
