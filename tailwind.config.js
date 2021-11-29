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
          '100': '#f9fcfa',
          '200': '#f1f9f3',
          '300': '#e1f0e4',
          '400': '#cae0d1',
          '500': '#648b6d',
          '600': '#476950',
          '700': '#335541',
          '800': '#1e3b29',
          '900': '#0f2a19'
        },
      }
    },
  },
  variants: {
    extend: {},
  },
  plugins: [],
}
