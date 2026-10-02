import { useNavigate } from 'react-router-dom'

export default function AdminDashboard() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <header className="bg-white border-b p-4 flex justify-between items-center shadow-sm">
        <h1 className="text-xl font-bold text-primary">FulfillIQ Platform Admin</h1>
        <button 
          onClick={() => {
            localStorage.removeItem('token')
            navigate('/login')
          }}
          className="text-sm text-gray-500 hover:text-black"
        >
          Logout
        </button>
      </header>
      
      <main className="flex-1 p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-gray-500 text-sm font-medium">Total Stores</h3>
            <p className="text-3xl font-bold">50</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-gray-500 text-sm font-medium">Products</h3>
            <p className="text-3xl font-bold">500</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <h3 className="text-gray-500 text-sm font-medium">Model Status</h3>
            <p className="text-xl font-semibold text-green-600 mt-2">Active</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border h-64 flex items-center justify-center">
            <p className="text-gray-400">Map Visualization Placeholder</p>
        </div>
      </main>
    </div>
  )
}
