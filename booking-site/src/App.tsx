import React, { useState } from 'react';
import { ShoppingBag, X, CheckCircle, ArrowRight, Package } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const PRODUCTS = [
  {
    id: 'prod-001',
    name: 'Neural Quantum Headphones',
    category: 'Electronics',
    price: 299.99,
    image: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&q=80&w=800'
  },
  {
    id: 'prod-002',
    name: 'AeroKnit Smart Sneakers',
    category: 'Apparel',
    price: 159.00,
    image: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&q=80&w=800'
  },
  {
    id: 'prod-003',
    name: 'Titanium Smartwatch Pro',
    category: 'Wearables',
    price: 499.50,
    image: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&q=80&w=800'
  },
  {
    id: 'prod-004',
    name: 'Minimalist Mechanical Keyboard',
    category: 'Accessories',
    price: 189.99,
    image: 'https://images.unsplash.com/photo-1595225476474-87563907a212?auto=format&fit=crop&q=80&w=800'
  },
];

function App() {
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [isBooking, setIsBooking] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    address: '',
    city: ''
  });

  const handleBook = (product: any) => {
    setSelectedProduct(product);
  };

  const submitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsBooking(true);
    
    try {
      // Create a booking payload to send to Head Office Agent
      const payload = {
        order_id: `ORD-${Math.floor(Math.random() * 100000)}`,
        product: selectedProduct,
        customer: formData,
        timestamp: new Date().toISOString()
      };

      // 1. Send data to Head Office Agent
      // Note: We use a public webhook endpoint we will create in the backend
      await axios.post(`${API_URL}/api/orders/webhook`, payload, {
        headers: {
          'X-Tunnel-Skip-Antiphishing-Page': 'true'
        }
      });
      
      // Reset and show success
      setSelectedProduct(null);
      setFormData({ name: '', email: '', address: '', city: '' });
      setShowToast(true);
      setTimeout(() => setShowToast(false), 5000);
    } catch (error) {
      console.error("Failed to book order:", error);
      alert("Failed to connect to the Head Office Agent. Ensure the backend is running.");
    } finally {
      setIsBooking(false);
    }
  };

  return (
    <>
      <nav className="navbar">
        <div className="brand">
          <ShoppingBag size={24} color="var(--accent)" />
          Nexus Store
        </div>
        <div style={{ color: 'var(--text-secondary)' }}>
          Demo Environment
        </div>
      </nav>

      <div className="container">
        <div className="header-section">
          <h1>Experience the Future of Retail</h1>
          <p>
            Book your next-gen products today. Orders are intelligently routed to our Head Office AI Agent for immediate fulfillment center allocation.
          </p>
        </div>

        <div className="product-grid">
          {PRODUCTS.map(product => (
            <div className="product-card" key={product.id}>
              <div style={{ overflow: 'hidden' }}>
                <img src={product.image} alt={product.name} className="product-image" />
              </div>
              <div className="product-info">
                <div className="product-category">{product.category}</div>
                <h3 className="product-title">{product.name}</h3>
                <div className="product-price">${product.price.toFixed(2)}</div>
                <button 
                  className="book-btn"
                  onClick={() => handleBook(product)}
                >
                  Book Now <ArrowRight size={18} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Booking Modal */}
      {selectedProduct && (
        <div className="modal-overlay" onClick={() => setSelectedProduct(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <button className="close-btn" onClick={() => setSelectedProduct(null)}>
              <X size={24} />
            </button>
            
            <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Complete Booking</h2>
            
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '12px' }}>
              <img src={selectedProduct.image} alt="" style={{ width: '60px', height: '60px', borderRadius: '8px', objectFit: 'cover' }} />
              <div>
                <h4 style={{ margin: '0 0 0.25rem 0' }}>{selectedProduct.name}</h4>
                <div style={{ color: 'var(--accent)', fontWeight: '600' }}>${selectedProduct.price.toFixed(2)}</div>
              </div>
            </div>

            <form onSubmit={submitOrder}>
              <div className="form-group">
                <label>Full Name</label>
                <input 
                  type="text" 
                  className="form-control" 
                  required 
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input 
                  type="email" 
                  className="form-control" 
                  required 
                  value={formData.email}
                  onChange={e => setFormData({...formData, email: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Delivery Address</label>
                <input 
                  type="text" 
                  className="form-control" 
                  required 
                  value={formData.address}
                  onChange={e => setFormData({...formData, address: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>City</label>
                <input 
                  type="text" 
                  className="form-control" 
                  required 
                  value={formData.city}
                  onChange={e => setFormData({...formData, city: e.target.value})}
                />
              </div>
              
              <button type="submit" className="submit-btn" disabled={isBooking}>
                {isBooking ? 'Processing...' : 'Confirm Booking'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Success Toast */}
      {showToast && (
        <div className="toast">
          <CheckCircle size={20} />
          <div>
            <strong>Booking Confirmed!</strong>
            <div style={{ fontSize: '0.85rem', opacity: 0.9 }}>Order sent to Head Office Agent for fulfillment.</div>
          </div>
        </div>
      )}
    </>
  );
}

export default App;
