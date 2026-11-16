import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/Shell";

export const metadata: Metadata = {
  title: "BRDashboard",
  description: "From cattle health data to better decisions.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preload" href="/fonts/RedHatDisplay-600.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/RedHatDisplay-500.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/RedHatMono-500.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
      </head>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
