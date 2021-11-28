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
    extend: {
      colors: {
        gray: {
          '100': '#D6DED4',
          '200': '#BFCEC3',
          '300': '#C1D1BC',
          '400': '#98A8A3',
          '500': '#6C7F77',
          '600': '#4D625D',
          '700': '#3B5A4A',
          '800': '#405147',
          '900': '#2C3635'
        },
      }
    },
  },
  variants: {
    extend: {},
  },
  plugins: [],
}
