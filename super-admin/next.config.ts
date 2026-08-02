import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "www.vinesflow.com",
        pathname: "/logo.png",
      },
    ],
  },
};

export default nextConfig;
