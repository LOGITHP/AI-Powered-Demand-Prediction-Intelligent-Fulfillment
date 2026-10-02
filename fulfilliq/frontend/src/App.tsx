import React, { createContext, FormEvent, useContext, useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, ArrowRight, Boxes, BrainCircuit, Check, ChevronRight, CircleHelp, ClipboardList, Clock3, LogOut, MapPin, Package, Plus, RefreshCw, Search, ShoppingBag, Sparkles, Store as StoreIcon, Truck, UserRound, WandSparkles } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import L from 'leaflet'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { api, errorMessage, Product, Store, User, roleHome } from './api'

type Candidate = Store & { fulfillment_score: number; availability_confidence: number; confidence_percentage: number; predicted_demand: number; expected_delivery: string; reasons: string[]; inventory: { reported_quantity: number; available_quantity: number }; score_components: Record<string, number> }
type Match = { product: Product; recommended_store: Candidate; alternatives: Candidate[] }
type CartItem = { product: Product; quantity: number; store: Candidate; customer_lat: number; customer_lng: number }
type ContextValue = { user: User | null; setUser: (v: User | null) => void; logout: () => void; cart: CartItem[]; setCart: (v: CartItem[]) => void }
const Context = createContext<ContextValue>(null as unknown as ContextValue)
const useSession = () => useContext(Context)
const cash = (v: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

function useApi<T>(key: unknown[], url: string, enabled = true) {
  return useQuery<T>({ queryKey: key, queryFn: async () => (await api.get(url)).data, enabled })
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [cart, setCart] = useState<CartItem[]>([])
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('fulfilliq_token')))
  useEffect(() => {
    if (!localStorage.getItem('fulfilliq_token')) return
    api.get('/auth/me').then((r) => setUser(r.data)).catch(() => localStorage.removeItem('fulfilliq_token')).finally(() => setLoading(false))
  }, [])
  const logout = () => { localStorage.removeItem('fulfilliq_token'); setUser(null); setCart([]) }
  if (loading) return <div className="loading-page"><span className="brand-mark">F</span><span className="spinner" />Opening your workspace</div>
  return <Context.Provider value={{ user, setUser, logout, cart, setCart }}><Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/" element={user?.role === 'PLATFORM_ADMIN' ? <Navigate to="/admin" /> : user?.role === 'STORE_MANAGER' ? <Navigate to="/store" /> : <CustomerLayout />}>
      <Route index element={<Shop />} /><Route path="cart" element={<CartPage />} /><Route path="orders" element={<CustomerOrders />} />
    </Route>
    <Route path="/store/*" element={user?.role === 'STORE_MANAGER' ? <Ops admin={false} /> : <Guard role="STORE_MANAGER" />} />
    <Route path="/admin/*" element={user?.role === 'PLATFORM_ADMIN' ? <Ops admin /> : <Guard role="PLATFORM_ADMIN" />} />
    <Route path="*" element={<Navigate to={roleHome(user?.role)} />} />
  </Routes></Context.Provider>
}

function Guard({ role }: { role: User['role'] }) {
  const { user } = useSession()
  if (!user) return <Navigate to="/login" state={{ from: role === 'PLATFORM_ADMIN' ? '/admin' : '/store' }} />
  return <main className="guard"><CircleHelp size={32} /><h1>That workspace is role protected</h1><p>Your account does not have access to this area.</p><Link className="button primary" to={roleHome(user.role)}>Go to my workspace</Link></main>
}

const schema = z.object({ email: z.string().email(), password: z.string().min(1), role: z.enum(['CUSTOMER', 'STORE_MANAGER', 'PLATFORM_ADMIN']).optional(), store_id: z.string().optional() })
function Login() {
  const { user, setUser } = useSession()
  const navigate = useNavigate()
  const location = useLocation()
  const [registering, setRegistering] = useState(false)
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(false)
  const { register, watch, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { role: 'CUSTOMER' } })
  const selectedRole = watch('role')
  const { data: stores = [] } = useApi<Store[]>(['public-stores'], '/stores', registering && selectedRole === 'STORE_MANAGER')

  if (user) return <Navigate to={roleHome(user.role)} />
  const submit = handleSubmit(async ({ email, password, role, store_id }) => {
    setBusy(true); setProblem('')
    try {
      const result = registering
        ? await api.post('/auth/register', { email, password, role, store_id: store_id ? Number(store_id) : undefined })
        : await api.post('/auth/login', new URLSearchParams({ username: email, password }), { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      localStorage.setItem('fulfilliq_token', result.data.access_token)
      setUser(result.data.user)
      navigate(location.state?.from || roleHome(result.data.user.role), { replace: true })
    } catch (e) { setProblem(errorMessage(e)) } finally { setBusy(false) }
  })
  return <div className="auth-page"><Link to="/" className="wordmark"><span className="brand-mark">F</span>Fulfill<span>IQ</span></Link><div className="auth-card">
    <div className="eyebrow">COIMBATORE · SIMULATED NETWORK</div><h1>{registering ? 'Create an account' : 'Welcome back'}</h1><p className="muted">Know what is in stock and where it can get to you.</p>
    <form className="form-stack" onSubmit={submit}>
      <label>Email address<input placeholder="you@example.com" {...register('email')} />{errors.email && <small className="field-error">Enter a valid email.</small>}</label>
      <label>Password<input type="password" placeholder="Password" {...register('password')} />{errors.password && <small className="field-error">Enter your password.</small>}</label>
      {registering && (
        <label>Account Type
          <select {...register('role')}>
            <option value="CUSTOMER">Customer</option>
            <option value="STORE_MANAGER">Store Manager</option>
            <option value="PLATFORM_ADMIN">Platform Admin</option>
          </select>
        </label>
      )}
      {registering && selectedRole === 'STORE_MANAGER' && (
        <label>Assign to Store
          <select {...register('store_id')}>
            <option value="">Select a store...</option>
            {stores.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.area})</option>)}
          </select>
        </label>
      )}
      {problem && <div className="alert error">{problem}</div>}<button className="button primary full" disabled={busy}>{busy ? 'Please wait…' : registering ? 'Create account' : 'Sign in'} <ArrowRight size={16} /></button>
    </form>
    <button className="text-button" onClick={() => setRegistering(!registering)}>{registering ? 'Already registered? Sign in' : 'Create an account'}</button>
    <div className="demo-accounts"><b>Development demo accounts</b><span>Admin · admin@fulfilliq.local</span><span>Manager · manager01@fulfilliq.local</span><span>Customer · customer@fulfilliq.local</span><code>Password: FulfillIQ-demo-2026!</code></div>
  </div><p className="auth-foot">All locations and orders are simulated. No real payment is collected.</p></div>
}

function CustomerLayout() {
  const { user, logout, cart } = useSession()
  return <div className="customer-app"><header className="customer-header"><Link className="wordmark" to="/"><span className="brand-mark">F</span>Fulfill<span>IQ</span></Link><div className="delivery-place"><MapPin size={17} /><span><small>Delivering around</small><b>Coimbatore, Tamil Nadu</b></span><ChevronRight size={15} /></div>
    <nav><Link to="/">Shop</Link>{user && <Link to="/orders">Orders</Link>}<Link to="/cart" className="bag-link"><ShoppingBag size={16} /> Bag{cart.length > 0 && <i>{cart.reduce((a, b) => a + b.quantity, 0)}</i>}</Link>{user ? <button className="account" onClick={logout}><UserRound size={15} />{user.email.split('@')[0]}<LogOut size={14} /></button> : <Link className="button dark small" to="/login">Sign in</Link>}</nav></header>
    <main className="customer-main"><Routes><Route index element={<Shop />} /><Route path="cart" element={<CartPage />} /><Route path="orders" element={<CustomerOrders />} /></Routes></main>
    <footer className="customer-footer"><span>FulfillIQ · fictional Coimbatore network</span><span>Availability confidence is a simulated estimate</span><Link to="/login">Team sign in</Link></footer></div>
}

function Shop() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [selected, setSelected] = useState<Product | null>(null)
  const [match, setMatch] = useState<Match | null>(null)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')
  const [location, setLocation] = useState({ lat: 11.0168, lng: 76.9558 })
  const productsQuery = useInfiniteQuery({
    queryKey: ['products', search, category],
    initialPageParam: 0,
    queryFn: async ({ pageParam }) => (await api.get('/products', { params: { limit: 48, offset: pageParam, search: search || undefined, category: category || undefined } })).data,
    getNextPageParam: (lastPage, pages) => pages.length * 48 < lastPage.total ? pages.length * 48 : undefined,
  })
  const data = productsQuery.data?.pages[0]
  const products = productsQuery.data?.pages.flatMap((page) => page.items) ?? []
  const { cart, setCart } = useSession()
  const groups = ['All', 'Grocery', 'Beverages', 'Personal Care', 'Household', 'Electronics', 'Stationery', 'Snacks', 'Fruits', 'Vegetables', 'Baby Care', 'Pet Care', 'Kitchen', 'Health & Wellness']
  const choose = async (product: Product) => {
    setSelected(product); setMatch(null); setProblem(''); setBusy(true)
    try { const r = await api.post('/recommend/store', { product_id: product.id, customer_lat: location.lat, customer_lng: location.lng, quantity: 1 }); setMatch(r.data) }
    catch (e) { setProblem(errorMessage(e)) } finally { setBusy(false) }
  }
  return <><section className="hero"><div><div className="eyebrow light"><i /> LIVE STOCK SIGNALS · COIMBATORE</div><h1>Good choices<br />start <em>in stock.</em></h1><p>See which nearby store can actually fulfill your order before checkout.</p><div className="hero-search"><Search size={19} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search 500+ everyday essentials" /><span>500+ items</span></div><div className="hero-facts"><span>50 simulated locations</span><span>Availability confidence</span><span>No payment required</span></div></div><div className="hero-art"><div className="hero-card"><small>LIVE AVAILABILITY</small><strong>91<span>%</span></strong><span>FulfillIQ confidence</span><hr /><b><MapPin size={14} /> FulfillIQ Store 017</b><small>4.1 km · Peelamedu</small></div><div className="floating-chip">✓ Ready to fulfill</div></div></section>
    <div className="section-heading"><div><div className="eyebrow">THE EVERYDAY EDIT</div><h2>{search ? 'Search results' : 'The essentials, nearby'}</h2><p>{data?.total ?? 0} products · estimated location <button onClick={() => { const lat = prompt('Enter latitude', String(location.lat)); const lng = prompt('Enter longitude', String(location.lng)); if (lat && lng && isFinite(+lat) && isFinite(+lng)) setLocation({ lat: +lat, lng: +lng }) }}>Change</button></p></div><span className="data-chip"><MapPin size={14} /> Coimbatore</span></div>
    <div className="category-strip">{groups.map((g) => <button className={category === (g === 'All' ? '' : g) ? 'category-chip active' : 'category-chip'} key={g} onClick={() => setCategory(g === 'All' ? '' : g)}>{g}</button>)}</div>
    {productsQuery.isLoading ? <Loading/> : <div className="product-grid">{products.map((p) => <article className="product-card" key={p.id} onClick={() => choose(p)}><div className="product-photo"><img src={p.image_url} alt={p.name} loading="lazy"/><span className="stock-tag">Check nearby stock</span><button><Plus size={18} /></button></div><div className="product-category">{p.category} · {p.unit}</div><h3>{p.name}</h3><div className="product-price"><b>{cash(p.price)}</b><small>Estimated price</small></div></article>)}</div>}
    {!productsQuery.isLoading && !products.length && <Empty title="No products found" text="Try a different search or category." />}
    {productsQuery.hasNextPage && <div className="load-more"><span>Showing {products.length} of {data?.total ?? 0} products</span><button className="button secondary" disabled={productsQuery.isFetchingNextPage} onClick={() => productsQuery.fetchNextPage()}>{productsQuery.isFetchingNextPage ? 'Loading more…' : 'Show more products'} <ArrowRight size={15}/></button></div>}
    <p className="disclaimer"><Sparkles size={15} /> Availability confidence combines reported stock, inventory reliability and near-term demand. Straight-line distance is an estimate.</p>
    {selected && <div className="modal-shade" onClick={() => setSelected(null)}><section className="match-modal" onClick={(e) => e.stopPropagation()}><button className="close" onClick={() => setSelected(null)}>×</button><div className="modal-product"><img src={selected.image_url} alt=""/><div><div className="eyebrow">STORE MATCH</div><h2>{selected.name}</h2><b>{cash(selected.price)}</b></div></div><hr/><div className="eyebrow">BEST AVAILABLE MATCH</div>
      {busy ? <Loading /> : match ? <><div className="best-store"><div><small>RECOMMENDED STORE</small><h3>{match.recommended_store.name}</h3><p>{match.recommended_store.area} · {match.recommended_store.distance_km} km estimated</p></div><strong>{match.recommended_store.confidence_percentage}%<small>CONFIDENCE</small></strong></div><div className="match-stats"><div><small>Fulfillment score</small><b>{match.recommended_store.fulfillment_score}<i>/100</i></b></div><div><small>Available units</small><b>{match.recommended_store.inventory.available_quantity}</b></div><div><small>Expected delivery</small><b>{match.recommended_store.expected_delivery}</b></div></div><ul className="reason-list">{match.recommended_store.reasons.map((r) => <li key={r}><Check size={14}/>{r}</li>)}</ul><button className="button primary full" onClick={() => { const existing = cart.find(c => c.product.id === selected.id && c.store.id === match.recommended_store.id); if (existing) { setCart(cart.map(c => c === existing ? { ...c, quantity: c.quantity + 1 } : c)) } else { setCart([...cart, { product: selected, quantity: 1, store: match.recommended_store, customer_lat: location.lat, customer_lng: location.lng }]) }; setSelected(null) }}>Add to bag · {cash(selected.price)}</button>
        {match.alternatives.length > 0 && <div className="alternatives"><b>Other nearby options</b>{match.alternatives.slice(0, 3).map((s) => <button key={s.id} onClick={() => { const existing = cart.find(c => c.product.id === selected.id && c.store.id === s.id); if (existing) { setCart(cart.map(c => c === existing ? { ...c, quantity: c.quantity + 1 } : c)) } else { setCart([...cart, { product: selected, quantity: 1, store: s, customer_lat: location.lat, customer_lng: location.lng }]) }; setSelected(null) }}><span>{s.name}<small>{s.area} · {s.distance_km} km</small></span><b>{s.confidence_percentage}% confidence</b></button>)}</div>}</> : <div className="alert error">{problem}</div>}
    </section></div>}
  </>
}

function CartPage() {
  const { cart, setCart, user } = useSession()
  const [problem, setProblem] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  const place = async () => {
    if (cart.length === 0) return
    if (!user) { navigate('/login', { state: { from: '/cart' } }); return }
    setBusy(true); setProblem('')
    try {
      const stores = Array.from(new Set(cart.map(c => c.store.id)))
      for (const storeId of stores) {
        const items = cart.filter(c => c.store.id === storeId)
        await api.post('/orders', { store_id: storeId, customer_lat: items[0].customer_lat, customer_lng: items[0].customer_lng, items: items.map(c => ({ product_id: c.product.id, quantity: c.quantity })) })
      }
      setCart([])
      navigate('/orders', { state: { placed: true } })
    } catch (e) { setProblem(errorMessage(e)) } finally { setBusy(false) }
  }
  if (cart.length === 0) return <Empty title="Your bag is ready for something good." text="Browse the catalog and choose a store with a strong availability signal." action={<Link to="/" className="button primary">Browse products <ArrowRight size={16}/></Link>} />
  const stores = Array.from(new Set(cart.map(c => c.store.id))).map(id => cart.find(c => c.store.id === id)?.store!)
  const totalQuantity = cart.reduce((a, b) => a + b.quantity, 0)
  const totalPrice = cart.reduce((a, b) => a + (b.product.price * b.quantity), 0)
  return <div className="cart-layout"><div><div className="eyebrow">YOUR BAG</div><h1>Ready when you are.</h1><p className="muted">Matched to nearby stores with stock confidence.</p>
    {cart.map((item, i) => <div className="cart-row" key={i}><img src={item.product.image_url}/><div><small>{item.product.category}</small><h3>{item.product.name}</h3><b>{cash(item.product.price)}</b><div className="quantity"><button onClick={() => item.quantity > 1 && setCart(cart.map((c, j) => j === i ? { ...c, quantity: c.quantity - 1 } : c))}>−</button>{item.quantity}<button onClick={() => setCart(cart.map((c, j) => j === i ? { ...c, quantity: c.quantity + 1 } : c))}>+</button></div></div><button className="text-button" onClick={() => setCart(cart.filter((_, j) => j !== i))}>Remove</button></div>)}
    <div className="selected-store">
      <Truck size={19}/><span><b>Fulfilling from {stores.length} store{stores.length > 1 ? 's' : ''}</b><small>{stores.map(s => s.name).join(', ')}</small></span><Check size={17}/>
    </div></div>
    <aside className="checkout"><div className="eyebrow">ORDER SUMMARY</div><h3>Quick checkout</h3><p><span>Items ({totalQuantity})</span><b>{cash(totalPrice)}</b></p><p><span>Delivery</span><b className="green">Included</b></p><hr/><p className="total"><span>Total</span><b>{cash(totalPrice)}</b></p><div className="payment-note"><Check size={14}/> Demo checkout · no payment collected</div>{problem && <div className="alert error">{problem}</div>}<button className="button primary full" disabled={busy} onClick={place}>{busy ? 'Placing order…' : 'Place demo order'} <ArrowRight size={16}/></button><small className="muted">Inventory is updated after placement.</small></aside></div>
}

function CustomerOrders() {
  const { user } = useSession()
  const { data, isLoading, error } = useApi<any[]>(['orders'], '/orders', Boolean(user))
  if (!user) return <Empty title="Your order history is waiting." text="Sign in to view simulated order tracking." action={<Link to="/login" state={{ from: '/orders' }} className="button primary">Sign in</Link>} />
  return <div className="orders-page"><div className="eyebrow">FULFILLMENT HISTORY</div><h1>Orders, in motion.</h1><p className="muted">Track each demo order from store selection through delivery.</p>{error && <QueryError error={error}/ >}{isLoading && <Loading />}{data?.map((o) => <article className="order-card" key={o.id}><div><div className="eyebrow">ORDER #{String(o.id).padStart(5, '0')}</div><h3>{o.items.map((x: any) => x.product_name + ' × ' + x.quantity).join(', ')}</h3><p>{o.store_name} · {new Date(o.timestamp).toLocaleString()}</p></div><Status value={o.status}/><div className="order-steps">{['Confirmed', 'Store selected', 'Preparing', 'Out for delivery', 'Delivered'].map((s, i) => <span key={s} className={i <= ['CONFIRMED','STORE_SELECTED','PREPARING','OUT_FOR_DELIVERY','DELIVERED'].indexOf(o.status) ? 'done' : ''}><i>{i + 1}</i>{s}</span>)}</div><div className="order-foot">Total <b>{cash(o.total_amount)}</b><small>Tracking is simulated</small></div></article>)}{!isLoading && !data?.length && <Empty title="No orders yet" text="Demo orders will appear here after checkout."/>}</div>
}

const managerLinks = [['/store', 'Overview'], ['/store/inventory', 'Inventory'], ['/store/forecast', 'Forecast & alerts'], ['/store/recommendations', 'Recommendations'], ['/store/orders', 'Incoming orders'], ['/store/events', 'Event ledger'], ['/store/reconciliation', 'Reconciliation']]
const adminLinks = [['/admin', 'Overview'], ['/admin/map', 'Network map'], ['/admin/inventory', 'Inventory'], ['/admin/orders', 'Orders'], ['/admin/predictions', 'Predictions'], ['/admin/analytics', 'Analytics'], ['/admin/events', 'Event ledger'], ['/admin/reconciliation', 'Reconciliation'], ['/admin/training', 'Model training'], ['/admin/simulation', 'Simulation'], ['/admin/catalog', 'Stores & products']]
function Ops({ admin }: { admin: boolean }) {
  const { user, logout } = useSession()
  const path = useLocation().pathname
  const links = admin ? adminLinks : managerLinks
  return <div className="ops-shell"><aside className="sidebar"><Link to={admin ? '/admin' : '/store'} className="wordmark"><span className="brand-mark">F</span>Fulfill<span>IQ</span></Link><small className="sidebar-caption">WORKSPACE</small><nav>{links.map(([url, label]) => <Link to={url} key={url} className={path === url ? 'nav-link active' : 'nav-link'}><span className="nav-dot"/>{label}{label === 'Model training' && <BrainCircuit size={15}/>}</Link>)}</nav><div className="sidebar-bottom"><span className="live-dot">●</span> SIMULATED COIMBATORE<button onClick={logout}><UserRound size={15}/>{user?.email}<LogOut size={15}/></button></div></aside><main className="ops-main"><header className="ops-top"><span>{admin ? 'Platform operations' : 'Store operations'} / <b>{links.find((x) => x[0] === path)?.[1]}</b></span><span className="data-chip">DEMO ENVIRONMENT</span></header><div className="ops-content"><Routes>{admin ? <>
    <Route index element={<AdminOverview/>}/><Route path="map" element={<AdminMap/>}/><Route path="inventory" element={<Inventory admin/>}/><Route path="orders" element={<OpsOrders admin/>}/><Route path="predictions" element={<Predictions/>}/><Route path="analytics" element={<Analytics/>}/><Route path="events" element={<EventLedger admin/>}/><Route path="reconciliation" element={<ReconciliationView admin/>}/><Route path="training" element={<Training/>}/><Route path="simulation" element={<Simulation/>}/><Route path="catalog" element={<Catalog/>}/>
  </> : <><Route index element={<StoreOverview/>}/><Route path="inventory" element={<Inventory admin={false}/>}/><Route path="forecast" element={<StoreForecast/>}/><Route path="recommendations" element={<Recommendations/>}/><Route path="orders" element={<OpsOrders admin={false}/>}/><Route path="events" element={<EventLedger admin={false}/>}/><Route path="reconciliation" element={<ReconciliationView admin={false}/>}/></>}</Routes></div></main></div>
}

function Title({ eyebrow, title, text, action }: { eyebrow: string; title: string; text: string; action?: React.ReactNode }) { return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{text}</p></div>{action}</div> }
function Panel({ title, subtitle, children, action }: { title: string; subtitle?: string; children: React.ReactNode; action?: React.ReactNode }) { return <section className="panel"><header><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>{action}</header>{children}</section> }
function KPI({ title, value, note, icon: Icon }: { title: string; value: string | number; note: string; icon: any }) { return <article className="kpi"><Icon size={17}/><small>{title}</small><b>{value}</b><span>{note}</span></article> }
function Status({ value }: { value: string }) { const k = value.toLowerCase(); return <span className={'status ' + (k.includes('high') ? 'red' : k.includes('medium') || k.includes('pending') ? 'amber' : k.includes('healthy') || k.includes('completed') ? 'green' : 'blue')}><i/>{value.replaceAll('_', ' ')}</span> }
function Empty({ title, text, action }: { title: string; text: string; action?: React.ReactNode }) { return <div className="empty"><Package size={23}/><h3>{title}</h3><p>{text}</p>{action}</div> }
function Loading() { return <div className="loading-row"><span className="spinner"/> Loading simulated data…</div> }
function QueryError({ error }: { error: unknown }) { return <div className="alert error">{errorMessage(error)}</div> }

function AdminOverview() {
  const { data, isLoading, error } = useApi<any>(['analytics'], '/admin/analytics')
  const chart = data?.hourly_demand ?? []
  return <><Title eyebrow="PLATFORM PULSE / COIMBATORE" title="A clear view of the network." text="Operational health and prediction activity from simulated locations." action={<Link className="button secondary" to="/admin/map">Open location map <ArrowRight size={15}/></Link>}/>{error && <QueryError error={error}/ >}{isLoading ? <Loading/> : <>
    <div className="kpi-grid"><KPI title="Active locations" value={data.stores} note={data.warehouses + ' warehouses'} icon={StoreIcon}/><KPI title="Products" value={data.products} note="Simulated catalog" icon={Package}/><KPI title="Active orders" value={data.active_orders} note="Order queue" icon={ClipboardList}/><KPI title="Availability confidence" value={data.average_availability_confidence + '%'} note={data.prediction_count + ' recorded predictions'} icon={Activity}/><KPI title="At reorder point" value={data.high_risk_items} note="Inventory records" icon={Boxes}/></div>
    <div className="dashboard-grid"><Panel title="Historical demand by hour" subtitle="Generated units across the historical order set"><div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart}><CartesianGrid vertical={false} stroke="#edf0ea"/><XAxis dataKey="hour" tickFormatter={(v) => v + ':00'} fontSize={11}/><YAxis fontSize={11}/><Tooltip/><Bar dataKey="units" fill="#3d8064" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div></Panel><Panel title="Network health" subtitle="Locations grouped by live inventory risk"><div className="risk-list">{(data.store_health || []).map((x: any) => <div key={x.risk}><span>{x.risk}</span><b>{x.count}</b><Status value={x.risk}/></div>)}</div><Link to="/admin/map" className="panel-link">View stores <ChevronRight size={14}/></Link></Panel></div>
    <p className="footnote">Simulated records only. Prediction confidence and demand are prototype estimates.</p></>}</>
}

function StoreOverview() {
  const { data, isLoading, error } = useApi<any>(['store'], '/store/dashboard')
  const { data: alerts = [] } = useApi<any[]>(['alerts'], '/store/alerts')
  const { data: recs = [] } = useApi<any[]>(['recs'], '/store/recommendations')
  if (isLoading) return <Loading/>
  if (error) return <QueryError error={error}/>
  return <><Title eyebrow={data.store.name + ' / STORE PULSE'} title="Your shift, at a glance." text={data.store.area + ', Coimbatore · Current simulated stock signals.'} action={<Link className="button secondary" to="/store/inventory">Review inventory <ArrowRight size={15}/></Link>}/><div className="kpi-grid"><KPI title="Inventory items" value={data.inventory_items} note="Product-store records" icon={Boxes}/><KPI title="Orders in motion" value={data.active_orders} note="Confirmed to delivery" icon={Truck}/><KPI title="Low-stock items" value={data.low_stock_items} note="At reorder point" icon={AlertTriangle}/><KPI title="Open alerts" value={alerts.length} note="Demand versus inventory" icon={Activity}/></div>
    <div className="dashboard-grid"><Panel title="Needs a closer look" subtitle="Predicted demand versus on-hand stock">{alerts.slice(0,6).map((a: any) => <div className="signal-row" key={a.id}><span><AlertTriangle size={15}/></span><b>{a.product_name}</b><small>{a.reported_quantity} stock · {a.predicted_demand} demand</small><Status value={a.risk}/></div>)}{!alerts.length && <Empty title="No alerts" text="Stock risk signals will appear here."/>}</Panel><Panel title="Suggested actions" subtitle="Replenishment queue">{recs.slice(0,4).map((r: any) => <div className="signal-row" key={r.id}><Sparkles size={15}/><b>{r.product_name}</b><small>Move {r.recommended_quantity} units</small><Status value={r.status}/></div>)}<Link to="/store/recommendations" className="panel-link">Open action queue <ChevronRight size={14}/></Link></Panel></div>
  </>
}

function Inventory({ admin }: { admin: boolean }) {
  const [search, setSearch] = useState('')
  const [notice, setNotice] = useState('')
  const { user } = useSession()
  const { data = [], isLoading, error, refetch } = useApi<any[]>(['inventory', admin, search], '/inventory?limit=600' + (search ? '&search=' + encodeURIComponent(search) : '') + (!admin && user?.store_id ? '&store_id=' + user.store_id : ''))
  const edit = async (row: any) => {
    const stock = prompt('Reported units for ' + row.product_name, String(row.reported_quantity))
    if (stock === null || !Number.isInteger(+stock) || +stock < 0) return
    try { await api.patch('/inventory/' + row.id, { reported_quantity: +stock, note: 'Dashboard stock count' }); setNotice('Inventory updated.'); refetch() } catch (e) { setNotice(errorMessage(e)) }
  }
  return <><Title eyebrow={admin ? 'GLOBAL INVENTORY' : 'STORE OPERATIONS'} title={admin ? 'Inventory visibility.' : 'Stock, as reported.'} text="Reported on-hand, reserved units and inventory reliability across the simulated network." action={<button className="button secondary" onClick={() => refetch()}><RefreshCw size={15}/> Refresh</button>}/>{notice && <div className="alert info">{notice}</div>}{error && <QueryError error={error}/ >}<Panel title={data.length + ' inventory records'} subtitle="Stock accuracy is a model feature, not a guarantee." action={<input className="table-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search product"/>}>{isLoading ? <Loading/> : <div className="table-wrap"><table><thead><tr><th>Product</th>{admin && <th>Store</th>}<th>Reported</th><th>Reserved</th><th>Available</th><th>Accuracy</th><th>Updated</th><th>Risk</th><th/></tr></thead><tbody>{data.map((r: any) => <tr key={r.id}><td><b>{r.product_name}</b><small>{r.sku} · {r.category}</small></td>{admin && <td>{r.store_name}</td>}<td>{r.reported_quantity}</td><td>{r.reserved_quantity}</td><td><b>{r.available_quantity}</b></td><td>{Math.round(r.inventory_accuracy * 100)}%</td><td>{new Date(r.last_updated).toLocaleString()}</td><td><Status value={r.reported_quantity <= r.reorder_level ? 'HIGH RISK' : 'HEALTHY'}/></td><td><button className="text-button" onClick={() => edit(r)}>Update</button></td></tr>)}</tbody></table></div>}</Panel></>
}

function StoreForecast() {
  const { data = [], isLoading, error } = useApi<any[]>(['alerts'], '/store/alerts')
  return <><Title eyebrow="NEXT SHIFT / FORECAST" title="Get ahead of the rush." text="Expected demand compared with stock and safety buffers."/>{error && <QueryError error={error}/ >}{isLoading ? <Loading/> : <div className="forecast-grid">{data.slice(0,24).map((r: any) => <article key={r.id} className="forecast-card"><Status value={r.risk}/><h3>{r.product_name}</h3><div className="match-stats"><div><small>ON HAND</small><b>{r.reported_quantity}</b></div><div><small>FORECAST</small><b>{r.predicted_demand}</b></div><div><small>SHORTAGE</small><b>{r.projected_shortage}</b></div></div><p>{r.category} · {r.safety_stock} safety-stock units</p></article>)}{!data.length && <Empty title="Inventory looks steady" text="No items currently need attention."/>}</div>}</>
}

function Recommendations() {
  const query = useQueryClient()
  const { data = [], isLoading, error } = useApi<any[]>(['recs'], '/store/recommendations')
  const act = async (id: number, verb: string) => { try { await api.post('/store/recommendations/' + id + '/' + verb); await query.invalidateQueries({ queryKey: ['recs'] }); await query.invalidateQueries({ queryKey: ['inventory'] }) } catch (e) { alert(errorMessage(e)) } }
  return <><Title eyebrow="FULFILLIQ ACTIONS" title="Small moves, fewer misses." text="Store-level replenishment steps based on forecast demand and current stock." action={<button className="button secondary" onClick={() => query.invalidateQueries({ queryKey: ['recs'] })}><RefreshCw size={15}/> Refresh</button>}/>{error && <QueryError error={error}/ >}{isLoading ? <Loading/> : <div className="recommend-grid">{data.map((r: any) => <article className="recommend-card" key={r.id}><Status value={r.status}/><div className="eyebrow">{r.store_name} · {r.action_type}</div><h3>{r.product_name}</h3><b className="move-qty">Move {r.recommended_quantity} units</b><p>{r.reason}</p><small>Deadline {r.deadline ? new Date(r.deadline).toLocaleTimeString() : 'next shift'}</small><div className="button-pair">{r.status === 'PENDING' && <button className="button secondary" onClick={() => act(r.id, 'acknowledge')}>Acknowledge</button>}{r.status !== 'COMPLETED' && <button className="button primary" onClick={() => act(r.id, 'complete')}>Mark completed <Check size={14}/></button>}</div></article>)}{!data.length && <Empty title="No recommendations" text="Recommendations are generated when expected demand reaches beyond inventory."/>}</div>}</>
}

function OpsOrders({ admin }: { admin: boolean }) {
  const { data = [], isLoading, error } = useApi<any[]>(['orders', admin], admin ? '/admin/orders' : '/store/orders')
  return <><Title eyebrow="SIMULATED ORDERS" title="Orders in motion." text="Order queue from the FulfillIQ customer checkout flow."/>{error && <QueryError error={error}/ >}{isLoading ? <Loading/> : <Panel title={data.length + ' recent orders'}><div className="table-wrap"><table><thead><tr><th>Order</th><th>Store</th><th>Products</th><th>Placed</th><th>Total</th><th>Status</th></tr></thead><tbody>{data.map((o: any) => <tr key={o.id}><td>#{String(o.id).padStart(5,'0')}</td><td>{o.store_name}</td><td>{o.items.map((i: any) => i.product_name + ' × ' + i.quantity).join(', ')}</td><td>{new Date(o.timestamp).toLocaleString()}</td><td>{cash(o.total_amount)}</td><td><Status value={o.status}/></td></tr>)}</tbody></table></div></Panel>}</>
}

const SOURCE_COLORS: Record<string, string> = { POS: '#3d8064', WMS: '#4a7fb5', ERP: '#b57a2e', RFID: '#8b5eb0' }

function EventLedger({ admin }: { admin: boolean }) {
  const { user } = useSession()
  const [source, setSource] = useState('')
  const [storeFilter, setStoreFilter] = useState('')
  const url = '/admin/events?limit=200' + (source ? '&source=' + source : '') + (!admin && user?.store_id ? '&store_id=' + user.store_id : '') + (storeFilter ? '&store_id=' + storeFilter : '')
  const { data = [], isLoading, error, refetch } = useApi<any[]>(['events', source, storeFilter, admin], url)
  const { data: summary } = useApi<any>(['source-summary'], '/admin/source-summary', admin)
  const fullForms: Record<string, string> = { POS: 'Point of Sale (POS)', WMS: 'Warehouse System (WMS)', ERP: 'Enterprise Resource Planning (ERP)', RFID: 'Radio Frequency ID (RFID)' }
  return <>
    <Title eyebrow={admin ? 'MULTI-SOURCE EVENT LEDGER' : 'STORE EVENT LEDGER'} title="Every signal, every source." text="POS, WMS, ERP and RFID events flowing into the inventory reconciliation engine." action={<button className="button secondary" onClick={() => refetch()}><RefreshCw size={15}/> Refresh</button>}/>
    {admin && summary && <div className="kpi-grid">{Object.entries(summary).map(([src, data]: [string, any]) => <KPI key={src} title={(fullForms[src] || src) + ' events'} value={data.total.toLocaleString()} note={Object.keys(data.event_types).length + ' event types'} icon={src === 'POS' ? StoreIcon : src === 'WMS' ? Boxes : src === 'RFID' ? Activity : ClipboardList}/>)}</div>}
    <Panel title={data.length + ' events'} subtitle="Most recent events across all sources." action={<div className="filter-row">
      <select value={source} onChange={(e) => setSource(e.target.value)}><option value="">All sources</option><option value="POS">Point of Sale (POS)</option><option value="WMS">Warehouse System (WMS)</option><option value="ERP">Enterprise Resource Planning (ERP)</option><option value="RFID">Radio Frequency ID (RFID)</option></select>
      {admin && <input className="table-search" value={storeFilter} onChange={(e) => setStoreFilter(e.target.value)} placeholder="Store ID"/>}
    </div>}>
      {error && <QueryError error={error}/>}{isLoading ? <Loading/> : <div className="table-wrap"><table><thead><tr><th>Source</th><th>Event</th><th>Store</th><th>Product</th><th>Δ Qty</th><th>Reported</th><th>Timestamp</th><th>Note</th></tr></thead><tbody>
        {data.map((e: any) => <tr key={e.id}><td><span className="source-badge" style={{ background: SOURCE_COLORS[e.source] || '#666' }}>{e.source}</span> <span className="source-label">{fullForms[e.source]?.replace(/ \(.+\)/, '') || e.source}</span></td><td>{e.event_type.replaceAll('_', ' ')}</td><td>Store {e.store_id}</td><td>#{e.product_id}</td><td className={e.quantity_delta > 0 ? 'text-green' : e.quantity_delta < 0 ? 'text-red' : ''}>{e.quantity_delta > 0 ? '+' : ''}{e.quantity_delta}</td><td>{e.reported_quantity ?? '—'}</td><td>{e.created_at ? new Date(e.created_at).toLocaleString() : '—'}</td><td><small>{e.note}</small></td></tr>)}
      </tbody></table></div>}
    </Panel>
  </>
}

function ReconciliationView({ admin }: { admin: boolean }) {
  const { user } = useSession()
  const [storeId, setStoreId] = useState(admin ? '1' : String(user?.store_id || '1'))
  const [productId, setProductId] = useState('1')
  const url = '/admin/reconciliation/' + storeId + '/' + productId
  const { data, isLoading, error, refetch } = useApi<any>(['reconciliation', storeId, productId], url, !!storeId && !!productId)
  const fullForms: Record<string, string> = { POS: 'Point of Sale (POS)', WMS: 'Warehouse System (WMS)', ERP: 'Enterprise Resource Planning (ERP)', RFID: 'Radio Frequency ID (RFID)' }
  return <>
    <Title eyebrow="INVENTORY RECONCILIATION" title="Four sources, one truth." text="Compare what POS, WMS, ERP and RFID report for the same SKU at the same store." action={<button className="button secondary" onClick={() => refetch()}><RefreshCw size={15}/> Refresh</button>}/>
    <Panel title="Lookup" subtitle="Enter a store and product to reconcile.">
      <div className="filter-row"><label>Store ID <input value={storeId} onChange={(e) => setStoreId(e.target.value)} type="number" min="1" style={{ width: 80 }}/></label><label>Product ID <input value={productId} onChange={(e) => setProductId(e.target.value)} type="number" min="1" style={{ width: 80 }}/></label><button className="button primary" onClick={() => refetch()}>Reconcile <ArrowRight size={15}/></button></div>
    </Panel>
    {error && <QueryError error={error}/>}{isLoading && <Loading/>}
    {data && <>
      <div className="kpi-grid">
        <KPI title="Reported quantity" value={data.current_reported_quantity ?? '—'} note="Current book value" icon={Package}/>
        <KPI title="Discrepancy spread" value={data.discrepancy_spread} note={data.discrepancy_spread >= 5 ? 'Sources strongly disagree' : data.discrepancy_spread >= 2 ? 'Minor disagreement' : 'Sources agree'} icon={AlertTriangle}/>
        <KPI title="Estimated confidence" value={Math.round(data.estimated_confidence * 100) + '%'} note={'Accuracy: ' + (data.inventory_accuracy ? Math.round(data.inventory_accuracy * 100) + '%' : 'N/A')} icon={Activity}/>
        <KPI title="Recommendation" value={data.recommendation.replaceAll('_', ' ')} note={data.total_events + ' total events'} icon={data.recommendation === 'VERIFY_IMMEDIATELY' ? AlertTriangle : data.recommendation === 'MONITOR' ? Activity : Check}/>
      </div>
      <Panel title="Source comparison" subtitle="Latest reported quantity from each data source.">
        <div className="reconciliation-grid">{Object.entries(data.sources).map(([src, info]: [string, any]) => (
          <article className="recon-card" key={src} style={{ borderTopColor: SOURCE_COLORS[src] || '#666' }}>
            <div>
              <span className="source-badge" style={{ background: SOURCE_COLORS[src] || '#666' }}>{src}</span>
              <span className="source-label-card">{fullForms[src]?.replace(/ \(.+\)/, '') || src}</span>
            </div>
            <b className="recon-qty">{info.latest_reported_quantity ?? '—'}</b>
            <small>Latest: {info.latest_event_type?.replaceAll('_', ' ') || 'None'}</small>
            <small>{info.event_count} events</small>
            <small>{info.latest_timestamp ? new Date(info.latest_timestamp).toLocaleString() : 'No data'}</small>
          </article>
        ))}</div>
      </Panel>
      <p className="footnote">Confidence is estimated from source agreement. A higher discrepancy spread lowers confidence. Verification is recommended when sources disagree by ≥5 units.</p>
    </>}
  </>
}

function AdminMap() {
  const { data = [], isLoading, error } = useApi<Store[]>(['map'], '/admin/map')
  const [selected, setSelected] = useState<Store | null>(null)
  const icon = (risk?: string) => {
    const color = risk === 'HIGH' ? '#cf6554' : risk === 'MEDIUM' ? '#e4ac47' : '#3e8e69'
    return L.divIcon({ className: 'marker', html: '<span style="background:' + color + '"></span>', iconSize: [20,20], iconAnchor: [10,10] })
  }
  return <><Title eyebrow="COIMBATORE / NETWORK" title="50 points of readiness." text="Fictional retail stores, dark stores and warehouses distributed across the city." action={<span className="data-chip">● Healthy　● Medium　● High risk</span>}/>{error && <QueryError error={error}/ >}{isLoading ? <Loading/> : <div className="map-layout"><div className="map-box"><MapContainer center={[11.0168,76.9558]} zoom={12} className="leaflet"><TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>{data.map((s) => <Marker key={s.id} position={[s.latitude,s.longitude]} icon={icon(s.risk)} eventHandlers={{ click: () => setSelected(s) }}><Popup>{s.name} · {s.risk}</Popup></Marker>)}</MapContainer></div><Panel title={selected?.name || 'Network health'} subtitle={selected ? selected.area + ' · ' + selected.type : data.length + ' active locations'}>{selected ? <><div className="store-health">{selected.inventory_health}<small>%</small><span>inventory health</span></div><p>Active orders <b>{selected.active_orders}</b></p><p>At-risk items <b>{selected.at_risk_items}</b></p><p>{selected.address}</p><Status value={selected.risk || 'HEALTHY'}/></> : data.slice(0,12).map((s) => <button className="map-list-row" onClick={() => setSelected(s)} key={s.id}><span>{s.name}<small>{s.area}</small></span><Status value={s.risk || 'HEALTHY'}/></button>)}</Panel></div>}</>
}

function Predictions() {
  const { data, isLoading, error } = useApi<any>(['predictions'], '/admin/predictions')
  return <><Title eyebrow="MODEL OUTPUTS" title="Predictions with context." text="Demand units and availability probability are separate signals."/>{error && <QueryError error={error}/ >}{isLoading ? <Loading/> : <div className="dashboard-grid"><Panel title="Demand predictions" subtitle="Expected units per product and store"><DataTable rows={data.demand} cols={['product','store','predicted_demand','model_version']}/></Panel><Panel title="Availability predictions" subtitle="Probability the request can be fulfilled"><DataTable rows={data.availability} cols={['product','store','confidence_percentage','reported_quantity']}/></Panel></div>}</>
}
function DataTable({ rows = [], cols }: { rows: any[]; cols: string[] }) { return <div className="table-wrap"><table><thead><tr>{cols.map((c) => <th key={c}>{c.replaceAll('_',' ')}</th>)}</tr></thead><tbody>{rows.slice(0,30).map((r: any, i: number) => <tr key={i}>{cols.map((c) => <td key={c}>{c === 'confidence_percentage' ? r[c] + '%' : r[c]}</td>)}</tr>)}</tbody></table>{!rows.length && <Empty title="No predictions saved" text="Run a customer recommendation or store forecast first."/>}</div> }

function Analytics() {
  const { data, isLoading, error } = useApi<any>(['evaluation'], '/admin/evaluation')
  return <><Title eyebrow="GENERATED DATA / EVALUATION" title="Measure the trade-offs." text="Compare nearest-store and FulfillIQ strategies against the same historical sample."/>{error && <QueryError error={error}/ >}{isLoading ? <Loading/> : <><div className="dashboard-grid"><Panel title="Nearest store baseline" subtitle={data.sample_size + ' generated orders sampled'}><h2>{data.baseline.successful_fulfillment_rate}%<small> success</small></h2><p>Average distance {data.baseline.average_distance_km} km</p><p>Stockout / failure {data.baseline.stockout_rate}%</p></Panel><Panel title="FulfillIQ fulfillment score" subtitle="Availability · inventory · distance · future risk"><h2>{data.fulfilliq.successful_fulfillment_rate}%<small> success</small></h2><p>Average distance {data.fulfilliq.average_distance_km} km</p><p>Stockout / failure {data.fulfilliq.stockout_rate}%</p></Panel></div><div className="alert info">{data.note}</div></>}</>
}

function Training() {
  const qc = useQueryClient()
  const { data: models = [], isLoading, error } = useApi<any[]>(['models'], '/admin/models')
  const { data: overview } = useApi<any>(['analytics'], '/admin/analytics')
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')
  const train = async (type: string) => { setBusy(type); setNotice(''); try { const { data } = await api.post('/admin/models/' + type + '/train'); setNotice(data.version_name + ' trained on ' + data.dataset_size.toLocaleString() + ' records. Metrics use an 80/20 holdout.'); await qc.invalidateQueries({ queryKey: ['models'] }) } catch(e) { setNotice(errorMessage(e)) } finally { setBusy('') } }
  const activate = async (id: number) => { setBusy(String(id)); try { await api.post('/admin/models/' + id + '/activate'); setNotice('Model activated for predictions.'); await qc.invalidateQueries({ queryKey: ['models'] }) } catch(e) { setNotice(errorMessage(e)) } finally { setBusy('') } }
  return <><Title eyebrow="MODEL TRAINING / ADMIN ONLY" title="Train on what happened." text="Retrain baseline forest models on generated history and inspect holdout metrics." action={<span className="data-chip">{Number(overview?.historical_orders || 0).toLocaleString()} records</span>}/>{notice && <div className="alert info">{notice}</div>}{error && <QueryError error={error}/ >}{isLoading ? <Loading/> : <><div className="training-grid">{(['demand','availability'] as const).map((type) => { const rows = models.filter((m) => m.model_type === type.toUpperCase()); const active = rows.find((m) => m.is_active); return <Panel key={type} title={type === 'demand' ? 'Demand model' : 'Availability model'} subtitle={type === 'demand' ? 'Random Forest Regressor · units by product, store and time' : 'Random Forest Classifier · probability of fulfilling a request'}><div className="eyebrow">{type === 'demand' ? 'DEMAND PREDICTION' : 'AVAILABILITY CONFIDENCE'}</div><p>{type === 'demand' ? 'Features: hour, weekday, month, product, store, promotions and inventory.' : 'Features: reported stock, request size, accuracy, inventory age, sales velocity and time.'}</p><button className="button primary" disabled={Boolean(busy)} onClick={() => train(type)}>{busy === type ? 'Training…' : 'Train / retrain'}</button>{active && <p className="active-version">Serving {active.version_name} · {JSON.stringify(active.metrics)}</p>}</Panel>})}</div><Panel title="Model registry" subtitle="Saved model versions and evaluated metrics"><DataTable rows={models.map((m) => ({ ...m, metrics: JSON.stringify(m.metrics), activate: m.is_active ? 'Active' : 'Activate' }))} cols={['version_name','model_type','dataset_size','metrics','activate']}/>{models.filter((m) => !m.is_active).map((m) => <button className="text-button registry-action" key={m.id} disabled={Boolean(busy)} onClick={() => activate(m.id)}>Activate {m.version_name}</button>)}</Panel></>}</>
}

function Simulation() {
  const qc = useQueryClient()
  const { data: state, refetch } = useApi<any>(['sim'], '/admin/simulation/state')
  const { data: scoreSettings } = useApi<any>(['score-settings'], '/admin/settings/fulfillment')
  const { data: stores = [] } = useApi<Store[]>(['stores'], '/stores')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [weights, setWeights] = useState<Record<string, number>>({ availability: 40, inventory: 20, distance: 20, future_availability: 10, delivery_sla: 10 })
  useEffect(() => { if (scoreSettings?.weights) setWeights(scoreSettings.weights) }, [scoreSettings])
  const step = async () => { setBusy(true); try { const { data } = await api.post('/admin/simulation/step'); setNotice('Simulation advanced to ' + new Date(data.simulated_at).toLocaleString() + '; ' + data.changes.length + ' inventory records updated.'); await refetch(); await qc.invalidateQueries({ queryKey: ['inventory'] }) } catch(e) { setNotice(errorMessage(e)) } finally { setBusy(false) } }
  const generate = async () => { setBusy(true); try { const { data } = await api.post('/admin/data/generate', { historical_orders: 100000, seed: 42 }); setNotice(data.products + ' products · ' + data.stores + ' stores · ' + data.historical_orders.toLocaleString() + ' historical records.'); await qc.invalidateQueries({ queryKey: ['analytics'] }) } catch(e) { setNotice(errorMessage(e)) } finally { setBusy(false) } }
  const [transfer, setTransfer] = useState({ from_store_id: 1, to_store_id: 23, product_id: 1, quantity: 5 })
  const submitTransfer = async (e: FormEvent) => { e.preventDefault(); setBusy(true); try { const { data } = await api.post('/admin/transfers', transfer); setNotice('Transfer complete: destination stock ' + data.before + ' + ' + data.transferred + ' = ' + data.after + '.'); await qc.invalidateQueries({ queryKey: ['inventory'] }) } catch(e) { setNotice(errorMessage(e)) } finally { setBusy(false) } }
  const saveWeights = async () => { setBusy(true); try { const { data } = await api.put('/admin/settings/fulfillment', weights); setNotice(data.note); await qc.invalidateQueries({ queryKey: ['score-settings'] }) } catch(e) { setNotice(errorMessage(e)) } finally { setBusy(false) } }
  const weightTotal = Object.values(weights).reduce((sum, value) => sum + value, 0)
  return <><Title eyebrow="SIMULATION LAB" title="Create the next scenario." text="Advance simulated stock events, increase history, and test store transfers." action={<span className="data-chip">Simulated time {state ? new Date(state.simulated_at).toLocaleString() : '—'}</span>}/>{notice && <div className="alert info">{notice}</div>}<div className="dashboard-grid"><Panel title="Hourly simulation step" subtitle="Apply generated orders against on-hand stock"><p>One hour advances the clock and records sales and inventory events.</p><button className="button primary" disabled={busy} onClick={step}>Advance one hour <ArrowRight size={15}/></button></Panel><Panel title="Data generator" subtitle="Grow the model training sample"><p>Reproducible seed 42 · Historical patterns vary by hour, day, category and location.</p><button className="button secondary" disabled={busy} onClick={generate}>Generate 100,000 order dataset</button></Panel></div><Panel title="Fulfillment score weights" subtitle="Adjust the transparent score components. Percentages must sum to 100."><div className="weight-editor">{Object.entries(weights).map(([key, value]) => <label key={key}>{key.replaceAll('_', ' ')}<div><input type="number" min="0" max="100" value={value} onChange={(e) => setWeights({ ...weights, [key]: +e.target.value })}/><span>%</span></div></label>)}<div className="weight-total"><small>TOTAL</small><b className={weightTotal === 100 ? 'green' : 'red-text'}>{weightTotal}%</b></div><button className="button primary" disabled={busy || weightTotal !== 100} onClick={saveWeights}>Save score weights</button></div></Panel><Panel title="Store-to-store transfer" subtitle="Both inventory ledgers and the transfer record are updated"><form className="transfer-form" onSubmit={submitTransfer}><label>From<select value={transfer.from_store_id} onChange={(e) => setTransfer({ ...transfer, from_store_id: +e.target.value })}>{stores.map((s) => <option key={s.id} value={s.id}>{s.name} · {s.area}</option>)}</select></label><label>To<select value={transfer.to_store_id} onChange={(e) => setTransfer({ ...transfer, to_store_id: +e.target.value })}>{stores.map((s) => <option key={s.id} value={s.id}>{s.name} · {s.area}</option>)}</select></label><label>Product ID<input type="number" value={transfer.product_id} onChange={(e) => setTransfer({ ...transfer, product_id: +e.target.value })}/></label><label>Units<input type="number" min="1" value={transfer.quantity} onChange={(e) => setTransfer({ ...transfer, quantity: +e.target.value })}/></label><button className="button primary" disabled={busy || transfer.from_store_id === transfer.to_store_id}>Transfer stock</button></form></Panel></>
}

function Catalog() {
  const qc = useQueryClient()
  const { data: stores = [] } = useApi<Store[]>(['admin-stores'], '/admin/stores')
  const { data: productData } = useApi<any>(['admin-products'], '/admin/products')
  const addProduct = async () => {
    const name = prompt('Product name')
    if (!name?.trim()) return
    const category = prompt('Category', 'Grocery') || 'Grocery'
    const price = Number(prompt('Estimated price in INR', '99') || '99')
    if (!Number.isFinite(price) || price < 0) return
    try {
      await api.post('/admin/products', { sku: 'FIQ-NEW-' + Date.now(), name, category, price, unit: '1 unit' })
      qc.invalidateQueries({ queryKey: ['admin-products'] })
    } catch(e) { alert(errorMessage(e)) }
  }
  const add = async () => { const name = prompt('Fictional store name'); if (!name) return; try { await api.post('/admin/stores', { name, type: 'DARK_STORE', latitude: 11.0168, longitude: 76.9558, area: 'Gandhipuram', address: 'Simulated Coimbatore location', capacity: 1000 }); qc.invalidateQueries({ queryKey: ['admin-stores'] }) } catch(e) { alert(errorMessage(e)) } }
  return <><Title eyebrow="NETWORK CONFIGURATION" title="Stores and products." text="Manage the fictional Coimbatore locations and catalog." action={<div className="button-pair"><button className="button secondary" onClick={add}><Plus size={15}/> Add location</button><button className="button primary" onClick={addProduct}><Plus size={15}/> Add product</button></div>}/><div className="kpi-grid"><KPI title="Locations" value={stores.length} note="Simulated stores" icon={StoreIcon}/><KPI title="Products" value={productData?.total || 0} note="Catalog records" icon={Package}/><KPI title="Store formats" value="3" note="Retail · dark · warehouse" icon={Boxes}/></div><Panel title="Location directory" subtitle="Fictional locations"><DataTable rows={stores} cols={['name','type','area','latitude','longitude','capacity']}/></Panel><Panel title="Product catalog" subtitle={(productData?.total || 0) + ' simulated products'}><DataTable rows={productData?.items || []} cols={['sku','name','category','price','brand']}/></Panel></>
}
