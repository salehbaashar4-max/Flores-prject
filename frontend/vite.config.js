import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// `--mode pages` builds for GitHub Pages project hosting under /Flores-prject/.
// Any other mode (e.g. Vercel's default production build) keeps the site at root.
export default defineConfig(({ mode }) => ({
  base: mode === 'pages' ? '/Flores-prject/' : '/',
  plugins: [react(), tailwindcss()],
  server: {
    // Honor a harness/host-assigned port (autoPort); fall back to Vite's default 5173.
    port: process.env.PORT ? Number(process.env.PORT) : 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
}))
