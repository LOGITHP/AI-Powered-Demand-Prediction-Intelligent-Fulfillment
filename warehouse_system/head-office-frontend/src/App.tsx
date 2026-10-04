import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import AIAgent from './pages/AIAgent';
import Alerts from './pages/Alerts';

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen font-sans overflow-hidden bg-gray-50 text-gray-900">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        {children}
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout><Dashboard /></AppLayout>} />
        <Route path="/agent" element={<AppLayout><AIAgent /></AppLayout>} />
        <Route path="/alerts" element={<AppLayout><Alerts /></AppLayout>} />
        
        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
