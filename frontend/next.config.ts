import type { NextConfig } from "next";
import { buildScopedHeaders } from "./app/lib/http/cache-policy";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  compress: true,
  generateEtags: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  async headers() {
    return buildScopedHeaders();
  },
};

export default nextConfig;
