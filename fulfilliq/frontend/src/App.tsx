import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import CustomerHome from './pages/Customer/Home'
import AdminDashboard from './pages/Admin/Dashboard'
import StoreDashboard from './pages/Store/Dashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        {/* Customer Routes */}
        <Route path="/customer" element={<CustomerHome />} />
        
        {/* Admin Routes */}
        <Route path="/admin" element={<AdminDashboard />} />
        
        {/* Store Manager Routes */}
        <Route path="/store" element={<StoreDashboard />} />
        
        {/* Default Redirect */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
