import { useNavigate } from 'react-router-dom'

export default function CustomerHome() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b p-4 flex justify-between items-center sticky top-0 z-10">
        <h1 className="text-xl font-bold text-primary">FulfillIQ App</h1>
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
      <main className="p-4 max-w-md mx-auto">
        <div className="bg-white p-4 rounded-lg shadow-sm border mb-4">
          <p className="text-sm text-gray-500">Delivery Location</p>
          <p className="font-medium truncate">Coimbatore, Tamil Nadu</p>
        </div>

        <div className="relative mb-6">
          <input 
            type="text" 
            placeholder="Search 'Wireless Mouse'..." 
            className="w-full border p-3 rounded-lg shadow-sm focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>

        <h2 className="font-semibold mb-3">Recommended for you</h2>
        <div className="grid grid-cols-2 gap-3">
           <div className="border rounded p-3 bg-white shadow-sm flex flex-col items-center">
             <div className="w-16 h-16 bg-gray-200 rounded mb-2 flex items-center justify-center text-gray-400">Image</div>
             <p className="text-sm font-medium text-center line-clamp-1">Wireless Mouse</p>
             <p className="text-xs text-green-600 mt-1 font-semibold">91% Availability</p>
           </div>
        </div>
      </main>
    </div>
  )
}
