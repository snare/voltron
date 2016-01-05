var path = require("path");
var webpack = require("webpack");
var BowerWebpackPlugin = require("bower-webpack-plugin");

module.exports = {
    entry: ['./app/index.jsx'],
    output: {
        path: './js',
        filename: 'bundle.js'
    },
    resolve: {
        modulesDirectories: ['node_modules', 'bower_components']
    },
    module: {
        loaders: [
            { test: /\.jsx$/, loader: 'jsx-loader' },
            { test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/,    loader: 'url-loader?limit=100000&mimetype=application/font-woff' },
            { test: /\.ttf(\?v=[0-9]\.[0-9]\.[0-9])?$/,         loader: 'url-loader?limit=100000' },
            { test: /\.eot(\?v=[0-9]\.[0-9]\.[0-9])?$/,         loader: 'url-loader?limit=100000' },
            { test: /\.css(\?v=[0-9]\.[0-9]\.[0-9])?$/,         loader: 'style-loader!css-loader' },
            {
                test: /\.(jpe?g|png|gif|svg)(\?v=[0-9]\.[0-9]\.[0-9])?$/i,
                loaders: [
                    'file?hash=sha512&digest=hex&name=[hash].[ext]',
                    'image-webpack?bypassOnDebug&optimizationLevel=7&interlaced=false'
                ]
            }
        ]
    },
    plugins: [
        new BowerWebpackPlugin()
    ]
}
