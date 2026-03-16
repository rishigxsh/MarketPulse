import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/prices": "http://localhost:8000",
      "/stocks": "http://localhost:8000",
      "/alerts": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
