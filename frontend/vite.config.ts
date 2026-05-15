import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const base = env.GITHUB_PAGES === "true" ? "/medchem-fragment-atlas/" : env.VITE_BASE_PATH || "/";

  return {
    base,
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": "http://localhost:8000",
        "/health": "http://localhost:8000"
      }
    }
  };
});
