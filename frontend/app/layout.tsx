import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "نوبت | رزرو آنلاین",
  description: "جست‌وجو و رزرو آنلاین برای کسب‌وکارهای خدماتی",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
