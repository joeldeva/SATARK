import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        gov: {
          primary: '#1A2A6C',
          primaryDark: '#121D4C',
          teal: '#0F6E56',
          green: '#1D9E75',
          amber: '#BA7517',
          red: '#E24B4A',
          surface: '#F7F8FA',
          border: '#D8DEE9'
        }
      },
      fontFamily: {
        sans: ['"Noto Sans"', '"Noto Sans Devanagari"', '"Noto Sans Tamil"', 'Arial', 'sans-serif']
      },
      boxShadow: {
        card: '0 1px 2px rgba(16, 24, 40, 0.08)'
      }
    }
  },
  plugins: []
} satisfies Config;
