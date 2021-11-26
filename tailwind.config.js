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
      gray: colors.gray,
      pink: colors.pink,
      green: colors.green,
      red: colors.red,
      yellow: colors.amber,
      blue: colors.sky
    },
    extend: {},
  },
  variants: {
    extend: {},
  },
  plugins: [],
}
