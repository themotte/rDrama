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
      blue: colors.sky
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
          '200': '#e5e7eb',
          '300': '#d1d7db',
          '400': '#9ba6af',
          '500': '#6a7680',
          '600': '#4d5b63',
          '700': '#374552',
          '800': '#1f2c37',
          '900': '#111c28'
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
