import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)

      const res = await axios.post('http://localhost:8000/auth/login', formData)
      const token = res.data.access_token
      
      // Decode JWT roughly to get role
      const payload = JSON.parse(atob(token.split('.')[1]))
      localStorage.setItem('token', token)
      
      if (payload.role === 'PLATFORM_ADMIN') navigate('/admin')
      else if (payload.role === 'STORE_MANAGER') navigate('/store')
      else navigate('/customer')

    } catch (err) {
      setError('Invalid credentials')
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-md border">
        <h1 className="text-2xl font-bold text-center mb-6 text-primary">FulfillIQ Login</h1>
        
        {error && <div className="mb-4 text-red-500 text-sm text-center">{error}</div>}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input 
              type="email" 
              className="w-full border p-2 rounded" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input 
              type="password" 
              className="w-full border p-2 rounded" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
          </div>
          <button type="submit" className="w-full bg-primary text-white p-2 rounded font-medium hover:bg-primary/90">
            Sign In
          </button>
        </form>

        <div className="mt-6 text-sm text-gray-500">
          <p>Demo Accounts:</p>
          <ul className="list-disc pl-5 mt-2">
            <li>admin@fulfilliq.local / admin123</li>
            <li>manager01@fulfilliq.local / manager123</li>
            <li>customer@fulfilliq.local / customer123</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
