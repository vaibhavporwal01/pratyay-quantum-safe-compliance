import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
