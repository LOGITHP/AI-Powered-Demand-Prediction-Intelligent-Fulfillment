import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Operations from './pages/Operations';
import Audit from './pages/Audit';
import Sidebar from './components/Sidebar';

import Forecasting from './pages/Forecasting';
import Workforce from './pages/Workforce';
import Analytics from './pages/Analytics';
import Optimization from './pages/Optimization';
import AIAgent from './pages/AIAgent';
import Alerts from './pages/Alerts';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900 relative">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-8 relative">
          {/* Overlay to grey out operations if they want to click */}
          {children}
        </main>
      </div>
    </div>
  );
};

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/operations" element={<ProtectedRoute><Operations /></ProtectedRoute>} />
      <Route path="/audit" element={<ProtectedRoute><Audit /></ProtectedRoute>} />
      
      <Route path="/forecasting" element={<ProtectedRoute><Forecasting /></ProtectedRoute>} />
      <Route path="/workforce" element={<ProtectedRoute><Workforce /></ProtectedRoute>} />
      <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
      <Route path="/optimization" element={<ProtectedRoute><Optimization /></ProtectedRoute>} />
      <Route path="/agent" element={<ProtectedRoute><AIAgent /></ProtectedRoute>} />
      <Route path="/alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
