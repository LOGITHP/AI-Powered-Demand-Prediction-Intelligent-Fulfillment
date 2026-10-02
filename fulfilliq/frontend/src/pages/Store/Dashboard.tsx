import { useNavigate } from 'react-router-dom'

export default function StoreDashboard() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <header className="bg-white border-b p-4 flex justify-between items-center shadow-sm">
        <h1 className="text-xl font-bold text-primary">Store Manager Dashboard</h1>
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
        <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg mb-6">
          <h3 className="text-yellow-800 font-bold mb-1">HIGH DEMAND ALERT</h3>
          <p className="text-yellow-700 text-sm">Predicted demand for "Wireless Mouse" exceeds current inventory. FulfillIQ recommends transferring 9 units.</p>
          <button className="mt-3 bg-yellow-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-yellow-700">Acknowledge Transfer</button>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h2 className="font-semibold text-lg mb-4">Current Inventory</h2>
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b text-sm text-gray-500">
                <th className="pb-2">Product</th>
                <th className="pb-2">Current Stock</th>
                <th className="pb-2">Predicted Demand</th>
                <th className="pb-2">Risk</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b">
                <td className="py-3">Wireless Mouse</td>
                <td className="py-3 font-medium">8</td>
                <td className="py-3 text-orange-600">14</td>
                <td className="py-3"><span className="bg-red-100 text-red-700 px-2 py-1 rounded text-xs font-bold">HIGH</span></td>
              </tr>
              <tr className="border-b">
                <td className="py-3">Aashirvaad Atta 5kg</td>
                <td className="py-3 font-medium">45</td>
                <td className="py-3">12</td>
                <td className="py-3"><span className="bg-green-100 text-green-700 px-2 py-1 rounded text-xs font-bold">LOW</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
