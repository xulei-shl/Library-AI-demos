import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "book-echoes.xulei-shl.asia",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "img3.doubanio.com",
        pathname: "/**",
      }
    ],
    formats: ["image/avif", "image/webp"],
    // 禁用图片优化，直接加载原图
    // 因为 Next.js 的图片优化 API 无法正确处理外部 CDN 域名
    unoptimized: true,
  },
};

export default nextConfig;
