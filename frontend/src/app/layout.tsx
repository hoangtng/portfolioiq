import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { AuthProvider } from "@/lib/auth-context";
import "./globals.css"

const inter = Inter({
  subsets: ["latin"],
  weight:  ["400", "500", "600", "700", "800"],
  variable: "--font-inter",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight:  ["400", "500", "700"],
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title:       "PortfolioIQ — Trading Dashboard",
  description: "Track positions, research stocks and options, set alerts, journal your trades.",
};

export const viewport: Viewport = {
  themeColor: "#060A0F",
  width:      "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
