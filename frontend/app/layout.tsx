import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "نوبت | رزرو آنلاین",
  description: "سامانه حرفه‌ای رزرو و نوبت‌دهی آنلاین",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}

