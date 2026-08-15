/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0B0F17',
        surface: '#111827',
        'surface-elevated': '#1F2937',
        border: '#1E293B',
        'border-accent': '#334155',
        primary: {
          50: '#F0F9FF',
          100: '#E0F2FE',
          400: '#38BDF8',
          500: '#0EA5E9',
          600: '#0284C7',
          700: '#0369A1',
        },
        cyber: {
          blue: '#3B82F6',
          cyan: '#06B6D4',
          green: '#10B981',
          yellow: '#F59E0B',
          red: '#EF4444',
          purple: '#8B5CF6',
        },
        risk: {
          low: '#10B981',
          medium: '#F59E0B',
          high: '#EF4444',
          critical: '#8B5CF6',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'cyber-glow': '0 0 20px rgba(6, 182, 212, 0.15)',
        'cyber-red-glow': '0 0 20px rgba(239, 68, 68, 0.2)',
      }
    },
  },
  plugins: [],
}
