import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Proxy /api to FastAPI so you avoid CORS during development.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } } },
});
