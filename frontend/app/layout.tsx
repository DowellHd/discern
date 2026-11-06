import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ServiceWorkerRegistration } from "./sw-register";
import { InstallBanner } from "./install-banner";
import { BackSoon } from "@/components/BackSoon";
import { BACK_SOON } from "@/lib/back-soon";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://discern.dowellstandley.com";

const appMetadata: Metadata = {
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
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Discern",
  },
};

const BACK_SOON_TITLE = "We'll be back soon · Discern";
const BACK_SOON_DESCRIPTION = "Discern is temporarily unavailable. Thanks for your patience.";

const backSoonMetadata: Metadata = {
  ...appMetadata,
  title: { absolute: BACK_SOON_TITLE },
  description: BACK_SOON_DESCRIPTION,
  openGraph: {
    ...appMetadata.openGraph,
    title: BACK_SOON_TITLE,
    description: BACK_SOON_DESCRIPTION,
  },
  twitter: {
    ...appMetadata.twitter,
    title: BACK_SOON_TITLE,
    description: BACK_SOON_DESCRIPTION,
  },
};

export const metadata: Metadata = BACK_SOON ? backSoonMetadata : appMetadata;

export const viewport: Viewport = {
  themeColor: "#4f46e5",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`h-full ${inter.variable}`}>
      <body className="min-h-full flex flex-col font-sans bg-slate-50 text-slate-800 antialiased">
        <ServiceWorkerRegistration />
        {!BACK_SOON && <InstallBanner />}
        {BACK_SOON ? <BackSoon /> : children}
      </body>
    </html>
  );
}
