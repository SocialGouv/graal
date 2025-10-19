import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { autoTypeGeneration } from './vite-plugins/auto-type-generation'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    autoTypeGeneration({
      watchPaths: [
        '../graal/api/routes/**/*.py',
        '../graal/api/models/**/*.py',
        '../graal/api/main.py'
      ],
      generateCommand: 'yarn generate-types:dev',
      debounceMs: 5000,
      generateOnStart: true
    })
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
