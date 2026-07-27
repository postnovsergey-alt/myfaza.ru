import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// Vite конфиг. Одна кодовая база на веб и Mini App —
// сборка одинаковая, обёртка навигации выбирается в рантайме (см. platform/).
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // injectManifest — используем свой SW-файл (нужен для push-хендлера).
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      registerType: "autoUpdate",
      injectManifest: {
        globPatterns: ["**/*.{js,css,html,svg,woff2}"],
      },
      manifest: {
        name: "Моя фаза",
        short_name: "Моя фаза",
        description: "Спокойный трекер цикла",
        theme_color: "#F5F1EA",
        background_color: "#F5F1EA",
        display: "standalone",
        start_url: "/",
        icons: [
          {
            src: "/icon-192.svg",
            sizes: "192x192",
            type: "image/svg+xml",
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      // dev-режим: /api/* → http://127.0.0.1:8000
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    target: "es2022",
    sourcemap: false,
    reportCompressedSize: true,
    // Порог предупреждения выбран под наш бюджет (NFR-3: < 250 КБ gzip)
    chunkSizeWarningLimit: 220,
  },
});
