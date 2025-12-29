import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // REPLACE 'repo-name' WITH YOUR ACTUAL GITHUB REPOSITORY NAME
  // Example: base: '/byzantine-readings/',
  base: '/ByzantineLiturgyReadings/', 
})
