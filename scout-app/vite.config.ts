import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import electron from "vite-plugin-electron"
import path from "path"

export default defineConfig({
  root: path.resolve(__dirname, "src/renderer"),
  plugins: [
    react(),
    electron([
      {
        entry: path.resolve(__dirname, "src/main/main.ts"),
        vite: {
          build: {
            outDir: path.resolve(__dirname, "dist-electron"),
            rollupOptions: {
              external: ["electron"],
            },
          },
        },
      },
      {
        entry: path.resolve(__dirname, "src/main/preload.ts"),
        vite: {
          build: {
            outDir: path.resolve(__dirname, "dist-electron"),
            rollupOptions: {
              external: ["electron"],
            },
          },
        },
        onstart(options) {
          options.reload()
        },
      },
    ]),
  ],
  build: {
    outDir: path.resolve(__dirname, "dist"),
    emptyOutDir: true,
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "src/renderer/src") },
  },
})
