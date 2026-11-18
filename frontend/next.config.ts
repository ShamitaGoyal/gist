import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  webpack: (config) => {
    config.resolve.alias.canvas = false;
    config.resolve.alias.encoding = false;
    // pdfjs-dist ships a prebundled module. Webpack's ESM wrapper crashes on it.
    config.module.rules.push({
      test: /pdfjs-dist[\\/]build[\\/]pdf(\.worker)?\.mjs$/,
      type: "javascript/auto",
    });
    return config;
  },
};

export default nextConfig;
