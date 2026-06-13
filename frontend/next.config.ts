import type { NextConfig } from "next";

// Without Docker: defaults to localhost (start.bat / npm run dev)
// With Docker:    docker-compose passes http://backend:8001 at build time
const backendUrl = process.env.BACKEND_URL || "http://localhost:8001";

const nextConfig: NextConfig = {
  // Produces a self-contained build — no node_modules needed at runtime.
  // Required for the slim Docker runner stage.
  output: "standalone",

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
