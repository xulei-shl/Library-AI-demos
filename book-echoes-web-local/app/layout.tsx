import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "书海回响",
  description: "基于上海图书馆借阅数据的书目推荐",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
