/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          root: '#080C14',
          card: '#0D1320',
          input: '#111827',
        },
        border: '#1A2535',
        accent: {
          gold: '#C9A84C',
          success: '#4CAF8C',
          error: '#E05C5C',
          info: '#4C7AE0',
        },
        text: {
          primary: '#E8ECF0',
          secondary: '#8B9CB6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
