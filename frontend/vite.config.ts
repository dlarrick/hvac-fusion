import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    lib: {
      entry: 'src/index.ts',
      name: 'HvacFusionCards',
      fileName: () => 'hvac-fusion-cards.js',
      formats: ['es']
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true
      }
    },
    sourcemap: true,
    minify: false // keep readable for MVP debugging
  }
});
