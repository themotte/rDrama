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
      transparent: 'transparent',
      current: 'currentColor',
      black: colors.black,
      white: colors.white,
      pink: colors.pink,
      green: colors.green,
      red: colors.red,
      yellow: colors.amber,
      blue: colors.sky
    },
    fontFamily: {
      'heading': ['Delius Swash Caps']
    },
    extend: {
      boxShadow: {
        'inset-b-white-07': '-1px -1px 1px rgba(255, 255, 255, 0.07) inset',
        'inset-t-white-05': '0 1px 0 rgba(255, 255, 255, 0.05) inset',
        'inset-t-white-10': '0 1px 0 rgba(255, 255, 255, 0.10) inset',
        'inset-r-white-05': '1px 0 0 rgba(255, 255, 255, 0.05) inset'
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
    extend: {},
  },
  plugins: [],
}
