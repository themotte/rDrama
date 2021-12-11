const colors = require('tailwindcss/colors')

module.exports = {
  mode: 'jit',
  purge: [
    'files/templates/**/*.html',
    'files/templates/*.html'
  ],
  darkMode: 'class', // or 'media' or 'class'
  theme: {
    colors: {
      primary: ({ opacityVariable, opacityValue }) => {
        if (opacityValue !== undefined) {
          return `rgba(var(--color-primary), ${opacityValue})`
        }
        if (opacityVariable !== undefined) {
          return `rgba(var(--color-primary), var(${opacityVariable}, 1))`
        }
        return `rgb(var(--color-primary))`
      },
      transparent: 'transparent',
      current: 'currentColor',
      black: colors.black,
      white: colors.white,
      pink: colors.pink,
      purple: colors.purple,
      green: colors.green,
      red: colors.red,
      yellow: colors.amber,
      blue: colors.sky,
      'twitter': '#00acee',
      'success': '#16a34a',
      'danger': '#dc2626',
      'blue': '#0369a1',
      'lightblue': '#0ea5e9',
      'gold': '#facc15'
      'silver': '#94a3b8',
      'lightgreen': '#84cc16'
    },
    fontFamily: {
      'sans-serif': ['Helvetica Neue', '-apple-system', 'BlinkMacSystemFont', 'Tahoma', 'Segoe UI', 'Helvetica', 'sans-serif', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol'],
      'heading': ['Delius Swash Caps'],
      'serif': ['Georgia'],
      'mono': 'SFMono-Regular,Consolas,Liberation Mono,Menlo,Courier,monospace'
    },
    extend: {
      boxShadow: {
        'inset-b-white-07': '-1px -1px 1px rgba(255, 255, 255, 0.07) inset',
        'inset-t-white-05': '0 1px 0 rgba(255, 255, 255, 0.05) inset',
        'inset-t-white-10': '0 1px 0 rgba(255, 255, 255, 0.10) inset',
        'inset-r-white-05': '1px 0 0 rgba(255, 255, 255, 0.05) inset'
      },
      zIndex: {
        '100': 100
      },
      colors: {
        gray: {
          '100': '#f4f6f4',
          '200': '#e5ebe7',
          '300': '#d1dbd5',
          '400': '#9bafa1',
          '500': '#6a8073',
          '600': '#4c6351',
          '700': '#37523e',
          '800': '#1f3726',
          '900': '#112817'
        },
      }
    },
  },
  variants: {
    extend: {
      backgroundColor: ['checked'],
      boxShadow: ['checked'],
      color: ['checked']
    },
  },
  plugins: [],
}
