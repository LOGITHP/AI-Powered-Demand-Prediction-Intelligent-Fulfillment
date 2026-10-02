import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  timeout: 120_000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fulfilliq_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export interface User {
  id: number
  email: string
  role: 'CUSTOMER' | 'STORE_MANAGER' | 'PLATFORM_ADMIN'
  store_id: number | null
}

export interface Product {
  id: number
  sku: string
  name: string
  category: string
  subcategory?: string
  brand?: string
  price: number
  unit: string
  image_url: string
}

export interface Store {
  id: number
  name: string
  type: string
  latitude: number
  longitude: number
  area: string
  address: string
  distance_km?: number
  inventory_health?: number
  risk?: string
  active_orders?: number
  at_risk_items?: number
}

export const roleHome = (role?: User['role']) =>
  role === 'PLATFORM_ADMIN' ? '/admin' : role === 'STORE_MANAGER' ? '/store' : '/'

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    return typeof detail === 'string' ? detail : error.message
  }
  return error instanceof Error ? error.message : 'Something went wrong.'
}
