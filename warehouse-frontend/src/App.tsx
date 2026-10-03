import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import MainLayout from './layouts/MainLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Recommendations from './pages/Recommendations';
import PlaceholderPage from './pages/PlaceholderPage';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="recommendations" element={<Recommendations />} />
        {/* Modules in Development */}
        <Route path="inbound" element={<PlaceholderPage title="Inbound Operations" description="Manage incoming shipments, receiving schedules, and dock door allocations." />} />
        <Route path="outbound" element={<PlaceholderPage title="Outbound Operations" description="Track picking, packing, and dispatch operations for outbound orders." />} />
        <Route path="orders" element={<PlaceholderPage title="Order Management" description="View and process live customer orders, batch priorities, and fulfillment status." />} />
        <Route path="inventory" element={<PlaceholderPage title="Inventory Control" description="Live tracking of SKUs, stock levels, bin locations, and automated replenishment." />} />
        <Route path="workers" element={<PlaceholderPage title="Workforce Management" description="Manage warehouse staff, skills routing, and real-time location tracking." />} />
        <Route path="attendance" element={<PlaceholderPage title="Attendance & Shifts" description="Monitor worker clock-ins, shift schedules, and absenteeism predictions." />} />
        <Route path="tasks" element={<PlaceholderPage title="Task Allocation" description="AI-Powered task distribution engine balancing workload across available staff." />} />
        <Route path="predictions" element={<PlaceholderPage title="Demand Predictions" description="AI models forecasting incoming order volume and optimal staffing needs." />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
