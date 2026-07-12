/** @type {import('next').NextConfig} */
import path from "node:path";

const nextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  turbopack: {
    root: path.resolve(".")
  }
};

export default nextConfig;
