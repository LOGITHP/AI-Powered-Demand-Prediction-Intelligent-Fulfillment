import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { ScanLine, LogIn } from 'lucide-react';

export default function Login() {
  const [username, setUsername] = useState('worker001');
  const [password, setPassword] = useState('worker123');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const res = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('role', res.data.role);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 text-slate-100">
      <div className="max-w-sm w-full bg-slate-800 p-8 rounded-xl border-t-4 border-blue-500 shadow-2xl">
        <div className="flex flex-col items-center mb-8">
          <ScanLine size={48} className="text-blue-500 mb-4" />
          <h2 className="text-2xl font-bold">Worker Check-In</h2>
        </div>
        
        {error && <div className="bg-red-500/20 text-red-400 p-3 rounded-lg mb-4 text-sm text-center">{error}</div>}
        
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Worker ID / Username"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-center focus:ring-2 focus:ring-blue-500 outline-none text-slate-100 text-lg tracking-wider"
            />
          </div>
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="PIN / Password"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-center focus:ring-2 focus:ring-blue-500 outline-none text-slate-100 text-lg tracking-wider"
            />
          </div>
          <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 text-lg transition-colors">
            <LogIn size={24} />
            Start Shift
          </button>
        </form>
      </div>
    </div>
  );
}
