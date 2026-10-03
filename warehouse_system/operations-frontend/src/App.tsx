import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import OperationsDashboard from './pages/OperationsDashboard';
import { LogOut } from 'lucide-react';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    window.location.href = '/login';
  };

  return (
    <div className="flex flex-col h-screen bg-slate-900 text-slate-100">
      <header className="bg-slate-800 border-b border-slate-700 p-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-blue-400">Warehouse Worker Terminal</h1>
          <p className="text-sm text-slate-400">Shift In Progress</p>
        </div>
        <button onClick={handleLogout} className="text-slate-400 hover:text-red-400 flex items-center gap-2">
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
      <Route path="/" element={<ProtectedRoute><OperationsDashboard /></ProtectedRoute>} />
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
