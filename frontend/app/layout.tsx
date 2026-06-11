import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Discern — Document Intelligence",
  description: "Extract structured data from paper church records using computer vision.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
