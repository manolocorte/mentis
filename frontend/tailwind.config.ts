import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        serif: ['"IBM Plex Serif"', 'Georgia', 'serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        // Refined pine green — used as a restrained accent, not the whole UI.
        mentis: {
          50: '#f1f6f3',
          100: '#dcebe1',
          200: '#bbd8c6',
          300: '#8fbda4',
          400: '#5d9a7c',
          500: '#3d7c5d',
          600: '#2f6a4c',
          700: '#27553e',
          800: '#234534',
          900: '#1d392c',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
