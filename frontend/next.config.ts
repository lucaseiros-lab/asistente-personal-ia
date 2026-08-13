import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Habilita `.next/standalone` para poder armar una imagen de Docker de
  // producción liviana (server.js autocontenido, sin necesitar node_modules
  // completo en la imagen final). Vercel tiene su propio pipeline de
  // build/output y este modo lo rompe (no encuentra
  // `.next/next-server.js.nft.json` donde su builder lo espera), así que
  // se aplica solo fuera de Vercel — Vercel define `VERCEL=1` en su
  // entorno de build automáticamente.
  ...(process.env.VERCEL ? {} : { output: "standalone" as const }),
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
      {
        source: "/sw.js",
        headers: [
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
        ],
      },
    ];
  },
};

export default nextConfig;
