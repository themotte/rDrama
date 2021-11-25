const colors = require('tailwindcss/colors')

module.exports = {
  //mode: 'jit',
  //purge: [
    //    '../../templates/**/*.html',
    //    '../../templates/*.html'
    //],*/
    prefix: 'z-',
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
      red: colors.rose,
      yellow: colors.amber
    },
    extend: {},
  },
  variants: {
    extend: {},
  },
  plugins: [],
}
