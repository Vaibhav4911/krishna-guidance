import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        night: '#0F172A',
        gold: '#E7C77A',
        sand: '#F7F0E6',
        zen: '#C8D8C4',
      },
      boxShadow: {
        soft: '0 12px 32px rgba(15, 23, 42, 0.12)',
      },
    },
  },
  plugins: [],
};

export default config;
