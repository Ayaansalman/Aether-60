import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", proxy: { "/api": process.env.AETHER_BACKEND_URL || "http://127.0.0.1:8000" } },
});
