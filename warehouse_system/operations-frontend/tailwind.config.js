/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0f172a',
        foreground: '#f8fafc',
        primary: '#3b82f6',
        secondary: '#1e293b',
        accent: '#8b5cf6',
        danger: '#ef4444',
        success: '#22c55e',
        warning: '#f59e0b',
        border: '#334155'
      }
    },
  },
  plugins: [],
}
