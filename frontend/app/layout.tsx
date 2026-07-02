import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ServiceWorkerRegistration } from "./sw-register";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://discern.dowellstandley.com";

export const metadata: Metadata = {
  title: {
    default: "Discern — Document Intelligence",
    template: "%s · Discern",
  },
  description: "Extract structured data from paper church records using computer vision.",
  metadataBase: new URL(BASE_URL),
  openGraph: {
    title: "Discern — Document Intelligence",
    description: "Extract structured data from paper church records using computer vision.",
    url: "/",
    siteName: "Discern",
    type: "website",
    images: [{ url: "/og.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Discern — Document Intelligence",
    description: "Extract structured data from paper church records using computer vision.",
    images: ["/og.png"],
  },
  themeColor: "#4f46e5",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Discern",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`h-full ${inter.variable}`}>
      <body className="min-h-full flex flex-col font-sans bg-slate-50 text-slate-800 antialiased">
        <ServiceWorkerRegistration />
        {children}
      </body>
    </html>
  );
}
