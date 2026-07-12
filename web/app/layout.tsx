import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "足球分析台",
  description: "足球比赛分析与盘口报告"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
