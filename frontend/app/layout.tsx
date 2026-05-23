import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "shortform-os",
  description: "Autonomous Viral Content Operating System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-gray-100 font-sans antialiased">
        <header className="border-b border-gray-800 px-6 py-4">
          <span className="text-lg font-semibold tracking-tight">shortform-os</span>
        </header>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
