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
      'font-heading': ['Arial']
    },
    extend: {
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
