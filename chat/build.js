require('dotenv').config()
const package = require("./package.json");
const path = require("path");
const { build } = require("esbuild");

const options = {
  entryPoints: ["./src/index.tsx"],
  outfile: path.resolve(__dirname, "../files/assets/js/chat_done.js"),
  bundle: true,
  minify: process.env.NODE_ENV === "production",
  define: {
    "process.env.VERSION": `"${package.version}"`,
    "process.env.NODE_ENV": `"${process.env.NODE_ENV}"`,
    "process.env.DEBUG": process.env.DEBUG,
    "process.env.FEATURES_ACTIVITY": process.env.FEATURES_ACTIVITY,
    "process.env.APPROXIMATE_CHARACTER_WIDTH": process.env.APPROXIMATE_CHARACTER_WIDTH,
  },
};

build(options).catch(() => process.exit(1));
