import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "墨迹与边界 - 中国作家地理叙事可视化",
  description: "通过交互式地图探索中国现代作家的创作轨迹与地理叙事",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
