import type { Metadata, Viewport } from "next";
import type { CSSProperties, ReactNode } from "react";
import "./globals.css";
import { AuthProvider } from "@/contexts/auth-context";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";
import { ToastProvider } from "@/components/ui/toast";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#1a56db",
};

export const metadata: Metadata = {
  title: "HostForGuest — AI-Powered Local Guide for Your Stay",
  description:
    "HostForGuest is an AI-powered platform that helps accommodation hosts provide personalized local guide experiences to their guests. Built by Syntagent.",
  keywords:
    "Croatia, tourism, hosts, AI recommendations, Istria, Kvarner, local guide, Syntagent",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
    apple: "/icon.svg",
  },
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "HostForGuest",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        style={{
          "--font-body": "Manrope, Inter, system-ui, sans-serif",
          "--font-display": '"Plus Jakarta Sans", Manrope, Inter, system-ui, sans-serif',
        } as CSSProperties}
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-white focus:shadow-lg"
        >
          Skip to main content
        </a>
        <RouteErrorBoundary>
          <AuthProvider>
            <ToastProvider>
              <div id="root">
                <main id="main-content" tabIndex={-1} className="outline-none">
                  {children}
                </main>
              </div>
            </ToastProvider>
          </AuthProvider>
        </RouteErrorBoundary>
      </body>
    </html>
  );
}
