import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import InboundDashboard from './pages/InboundDashboard';
import OutboundDashboard from './pages/OutboundDashboard';
import { LogOut } from 'lucide-react';

const ProtectedRoute = ({ children, title }: { children: React.ReactNode, title?: string }) => {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    window.location.href = '/login';
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900">
      <header className="bg-white border-b border-gray-200 p-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-blue-600">{title || "Inbound Operations Terminal"}</h1>
          <p className="text-sm text-gray-500">Intake Forecasting</p>
        </div>
        <button onClick={handleLogout} className="text-gray-500 hover:text-red-400 flex items-center gap-2">
          <LogOut size={20} />
          Logout
        </button>
      </header>
      <main className="flex-1 overflow-y-auto p-6">
        {children}
      </main>
    </div>
  );
};

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Navigate to="/inbound" replace />} />
      <Route path="/inbound" element={<ProtectedRoute title="Inbound Operations Terminal"><InboundDashboard /></ProtectedRoute>} />
      <Route path="/outbound" element={<ProtectedRoute title="Outbound Delivery Terminal"><OutboundDashboard /></ProtectedRoute>} />
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
