import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(),
  VueDevTools()],
  server: {
    port: 5173,      // Sets the dev server port
    strictPort: true, // If 5173 is in use, Vite will fail instead of picking 5174
  },
  // REPLACE 'repo-name' WITH YOUR ACTUAL GITHUB REPOSITORY NAME
  // Example: base: '/byzantine-readings/',
  base: '/ByzantineLiturgyReadings/',
})
