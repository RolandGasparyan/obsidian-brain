import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

// Proxy /api requests to the production VPS during local dev so
// `LiveBotsPanel` can poll real bot status without us having to run
// the JSON generator locally. In production, nginx serves
// /api/bots.json as a static file so this proxy is unused.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: "http://167.71.24.86",
        changeOrigin: true,
      },
    },
  },
})
