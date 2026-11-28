import type { NextConfig } from "next";


const nextConfig: NextConfig = {
  // Allow the local development server to accept requests from this LAN host.
  allowedDevOrigins: ["192.168.29.81"],

  // build:check writes to .next-build so it never touches the dev server's .next.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",

  // Browser calls /api/* on this site; Next forwards them to the FastAPI service.
  async rewrites() {
    const api = process.env.API_URL ?? "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/health/:path*", destination: `${api}/health/:path*` },
    ];
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};


export default nextConfig;
