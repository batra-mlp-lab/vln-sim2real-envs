const path = require('path');

module.exports = {
  mode: 'development',
  entry: './src/index.js',
  output: {
    path: path.resolve(__dirname, '.'),
    filename: 'bundle.js'
  },
  target: 'web',
  devtool: 'inline-source-map',
  devServer: {
    port: 80,
    open: true
  },
  node: {
   fs: "empty"
  }
};
