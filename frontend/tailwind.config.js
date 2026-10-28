/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { 950: '#07090d', 900: '#0b0f14', 850: '#0f141b', 800: '#131a23', 700: '#1c2531', 600: '#2a3542', 500: '#3b4857' },
        fg: { DEFAULT: '#d8e1ea', muted: '#8696a7', dim: '#5d6b7a' },
        amber: { DEFAULT: '#f5b942', soft: '#f5b94222' },
        buy: { DEFAULT: '#22c55e', soft: '#22c55e1f' },
        sell: { DEFAULT: '#f0525a', soft: '#f0525a1f' },
        info: '#4ea8ff',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
