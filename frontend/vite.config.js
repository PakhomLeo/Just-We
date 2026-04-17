import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/assets/styles/variables" as *;`,
        // Suppress legacy-js-api warning from Vite/Sass compatibility
        silenceDeprecations: ['legacy-js-api']
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Split echarts into its own chunk
          'echarts': ['echarts'],
          // Split element-plus into its own chunk
          'element-plus': ['element-plus'],
        }
      }
    },
    // Enable source map for better debugging
    sourcemap: false,
    // Target modern browsers for smaller bundles
    target: 'es2015',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
