export default {
  plugins: {
    '@tailwindcss/postcss': {}, // 关键改动点：加上 @ 符号和 /postcss
    autoprefixer: {},
  },
}