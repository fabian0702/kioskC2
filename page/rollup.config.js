import terser from '@rollup/plugin-terser';

export default {
  input: 'src/bundle.js',
  output: {
    file: 'dist/bundle.min.js',
    format: 'iife',
    inlineDynamicImports: true,
    sourcemap: true // optional but useful
  },
  plugins: [
    terser({
        compress: {
            drop_console: true
        },
        mangle: {
            toplevel: true
        },
        format: {
            comments: false
        }
    })
  ],
  preserveSymlinks: true
};