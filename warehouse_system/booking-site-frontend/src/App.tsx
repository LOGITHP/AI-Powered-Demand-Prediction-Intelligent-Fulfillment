import { useState } from 'react'
import { Hexagon, Truck, Calendar, MapPin, CheckCircle, Clock, Zap, ShoppingCart } from 'lucide-react'
import axios from 'axios'

const PRODUCTS = [
  { id: 1, name: 'Smartphones / Mobile Devices', weightPerUnit: 0.5 },
  { id: 2, name: 'Laptops / Computers', weightPerUnit: 2.0 },
  { id: 3, name: 'Apparel / Clothing', weightPerUnit: 1.0 },
  { id: 4, name: 'Home Appliances', weightPerUnit: 15.0 },
]

function App() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    origin: '',
    destination: '',
    date: '',
    productId: 1,
    quantity: 1,
    type: 'standard'
  })
  
  const [isSubmitting, setIsSubmitting] = useState(false)

  const selectedProduct = PRODUCTS.find(p => p.id === formData.productId)
  const totalWeight = selectedProduct ? selectedProduct.weightPerUnit * formData.quantity : 0

  const handleBook = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    
    try {
      // Generate a random order ID
      const orderId = 'ORD-' + Math.floor(Math.random() * 100000);
      // Send booking to Head Office Agent on port 8001
      await axios.post(`http://localhost:8001/api/v1/orders/${orderId}/allocate`, {
        order_id: orderId,
        destination: formData.destination || 'Customer HQ',
        priority: formData.type === 'express' ? 'HIGH' : 'NORMAL',
        items: [
          {
            product_id: selectedProduct ? selectedProduct.name : 'Unknown Product',
            quantity: formData.quantity
          }
        ]
      })
      
      setStep(3)
    } catch (error) {
      console.error('Failed to book shipment', error)
      alert('Failed to book shipment. Is the Head Office Agent running?')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="bg-indigo-600 p-2 rounded-lg">
              <Hexagon className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">FulfillIQ Booking</span>
          </div>
          <nav className="flex gap-6">
            <a href="#" className="text-gray-600 hover:text-indigo-600 font-medium">Services</a>
            <a href="#" className="text-gray-600 hover:text-indigo-600 font-medium">Track</a>
            <a href="#" className="text-indigo-600 font-medium">Book Now</a>
          </nav>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-12">
        {step === 1 && (
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
            <div className="bg-indigo-600 px-8 py-10 text-white text-center">
              <h1 className="text-3xl font-bold mb-2">Book Your Products</h1>
              <p className="text-indigo-100">Intelligently routed by our Head Office Agent across the network.</p>
            </div>
            
            <div className="p-8">
              <form onSubmit={() => setStep(2)} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                      <MapPin className="w-4 h-4 text-gray-400"/> Origin Supplier
                    </label>
                    <input 
                      required
                      type="text" 
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                      placeholder="Supplier Name / Location"
                      value={formData.origin}
                      onChange={(e) => setFormData({...formData, origin: e.target.value})}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                      <MapPin className="w-4 h-4 text-gray-400"/> Destination
                    </label>
                    <input 
                      required
                      type="text" 
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                      placeholder="Delivery Location"
                      value={formData.destination}
                      onChange={(e) => setFormData({...formData, destination: e.target.value})}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                      <Calendar className="w-4 h-4 text-gray-400"/> Preferred Date
                    </label>
                    <input 
                      required
                      type="date" 
                      className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                      value={formData.date}
                      onChange={(e) => setFormData({...formData, date: e.target.value})}
                    />
                  </div>
                  <div className="md:col-span-2 flex gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                        <ShoppingCart className="w-4 h-4 text-gray-400"/> Product
                      </label>
                      <select 
                        required
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                        value={formData.productId}
                        onChange={(e) => setFormData({...formData, productId: parseInt(e.target.value)})}
                      >
                        {PRODUCTS.map(p => (
                          <option key={p.id} value={p.id}>{p.name} ({p.weightPerUnit} kg/unit)</option>
                        ))}
                      </select>
                    </div>
                    <div className="w-32">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Quantity
                      </label>
                      <input 
                        required
                        type="number"
                        min="1"
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                        value={formData.quantity}
                        onChange={(e) => setFormData({...formData, quantity: parseInt(e.target.value) || 1})}
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">Service Level</label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <label className={`border-2 rounded-xl p-4 cursor-pointer transition-all ${formData.type === 'standard' ? 'border-indigo-600 bg-indigo-50' : 'border-gray-200 hover:border-indigo-200'}`}>
                      <input 
                        type="radio" 
                        name="type" 
                        value="standard" 
                        className="sr-only"
                        checked={formData.type === 'standard'}
                        onChange={() => setFormData({...formData, type: 'standard'})}
                      />
                      <div className="flex items-center gap-3">
                        <Truck className={`w-6 h-6 ${formData.type === 'standard' ? 'text-indigo-600' : 'text-gray-400'}`} />
                        <div>
                          <h4 className={`font-semibold ${formData.type === 'standard' ? 'text-indigo-900' : 'text-gray-700'}`}>Standard Delivery</h4>
                          <p className="text-xs text-gray-500 mt-1">3-5 business days</p>
                        </div>
                      </div>
                    </label>
                    <label className={`border-2 rounded-xl p-4 cursor-pointer transition-all ${formData.type === 'express' ? 'border-indigo-600 bg-indigo-50' : 'border-gray-200 hover:border-indigo-200'}`}>
                      <input 
                        type="radio" 
                        name="type" 
                        value="express" 
                        className="sr-only"
                        checked={formData.type === 'express'}
                        onChange={() => setFormData({...formData, type: 'express'})}
                      />
                      <div className="flex items-center gap-3">
                        <Zap className={`w-6 h-6 ${formData.type === 'express' ? 'text-indigo-600' : 'text-gray-400'}`} />
                        <div>
                          <h4 className={`font-semibold ${formData.type === 'express' ? 'text-indigo-900' : 'text-gray-700'}`}>Express Delivery</h4>
                          <p className="text-xs text-gray-500 mt-1">1-2 business days</p>
                        </div>
                      </div>
                    </label>
                  </div>
                </div>

                <div className="pt-4 border-t border-gray-100">
                  <button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-4 rounded-xl shadow-md hover:shadow-lg transition-all flex justify-center items-center gap-2">
                    Continue to Review
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
            <div className="px-8 py-6 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">Review Booking</h2>
              <button onClick={() => setStep(1)} className="text-indigo-600 text-sm font-medium hover:underline">Edit Details</button>
            </div>
            
            <div className="p-8 space-y-6">
              <div className="bg-slate-50 p-6 rounded-xl border border-gray-200 space-y-4">
                <div className="flex justify-between pb-4 border-b border-gray-200">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">From</p>
                    <p className="font-semibold text-gray-900">{formData.origin}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-500 mb-1">To</p>
                    <p className="font-semibold text-gray-900">{formData.destination}</p>
                  </div>
                </div>
                <div className="flex justify-between pt-2">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Product Details</p>
                    <p className="font-medium text-gray-900">{formData.quantity}x {selectedProduct?.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-500 mb-1">Service Type</p>
                    <p className="font-medium text-indigo-600 capitalize">{formData.type}</p>
                  </div>
                </div>
                <div className="flex justify-between pt-2 border-t border-gray-100 mt-2">
                  <div>
                    <p className="text-sm text-gray-500 mb-1 flex items-center gap-1"><Clock className="w-3 h-3"/> Total Computed Weight</p>
                    <p className="font-semibold text-gray-800">{totalWeight} kg</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-500 mb-1 flex items-center justify-end gap-1"><Zap className="w-3 h-3"/> Est. Transit</p>
                    <p className="font-semibold text-emerald-600">
                      {formData.type === 'express' ? '1 Day, 4 Hours' : '3 Days, 12 Hours'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100">
                <div className="flex justify-between text-lg font-bold text-gray-900 mb-6">
                  <span>Estimated Quote</span>
                  <span>${formData.type === 'express' ? (totalWeight * 2.5).toFixed(2) : (totalWeight * 1.2).toFixed(2)}</span>
                </div>
                
                <button 
                  onClick={handleBook}
                  disabled={isSubmitting}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-semibold py-4 rounded-xl shadow-md transition-all flex justify-center items-center gap-2"
                >
                  {isSubmitting ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                      Sending to Head Office...
                    </span>
                  ) : "Confirm & Send to Routing Agent"}
                </button>
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100 text-center p-12">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 mb-6">
              <CheckCircle className="w-10 h-10 text-green-600" />
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Routed Successfully!</h2>
            <p className="text-gray-600 max-w-md mx-auto mb-8">
              Your shipment was received by the Head Office Agent and has been automatically routed to the nearest available warehouse for processing.
            </p>
            <div className="bg-gray-50 p-4 rounded-lg inline-block border border-gray-200">
              <p className="text-sm text-gray-500 mb-1">Global Tracking Code</p>
              <p className="text-xl font-mono font-bold text-indigo-700">HQ-NET-{Math.floor(100000 + Math.random() * 900000)}</p>
            </div>
            <div className="mt-10">
              <button onClick={() => {
                setStep(1)
                setFormData({origin: '', destination: '', date: '', productId: 1, quantity: 1, type: 'standard'})
              }} className="text-indigo-600 font-semibold hover:underline">
                Book Another Product
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
