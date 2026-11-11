import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // fail loudly if an old copy still holds the port, instead of silently starting on 5174
  },
  // Frontend unit tests (npm test): run in a simulated browser (jsdom).
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.js"],
    globals: true,
  },
});
