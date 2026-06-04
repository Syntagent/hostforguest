import type { NextConfig } from "next";
import { config } from "dotenv";
import path from "path";
import withPWAInit from "@ducanh2912/next-pwa";

// Load environment variables from the root .env file
config({ path: path.resolve(process.cwd(), "../.env") });

/**
 * next-pwa can break Next.js 15 App Router prerender of `/_not-found` (build fails with
 * "Cannot find module for page: /_not-found/page"). Enable only when explicitly requested.
 */
const nextPwaExplicitlyEnabled =
  process.env.NODE_ENV !== "development" && process.env.NEXT_PWA === "true";

const withPWA = withPWAInit({
  dest: "public",
  cacheOnFrontEndNav: true,
  aggressiveFrontEndNavCaching: true,
  reloadOnOnline: true,
  disable: process.env.NODE_ENV === "development" || !nextPwaExplicitlyEnabled,
  workboxOptions: {
    disableDevLogs: true,
  },
});

const apiProxyTarget = (() => {
  if (process.env.API_PROXY_TARGET?.trim()) {
    return process.env.API_PROXY_TARGET.trim().replace(/\/$/, "");
  }
  // Local dev: always proxy to local API (ignore NEXT_PUBLIC_API_URL pointing at prod).
  if (process.env.NODE_ENV === "development") {
    return "http://127.0.0.1:8000";
  }
  return (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
})();

const nextConfig: NextConfig = {
  output: "standalone",
  /** Repo has a root package-lock + frontend lockfile; anchor tracing to this app (silences warning, stabilizes chunks). */
  outputFileTracingRoot: path.resolve(process.cwd()),
  /** ESM-heavy / mixed packages: avoid broken dynamic chunks in dev (Next 15 + Webpack). */
  transpilePackages: ["framer-motion", "leaflet", "react-leaflet"],
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget}/api/:path*`,
      },
    ];
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  env: {
    GOOGLE_MAPS_API_KEY: process.env.GOOGLE_MAPS_API_KEY,
    // Single key in root .env: GOOGLE_MAPS_API_KEY — client code uses NEXT_PUBLIC_* name
    NEXT_PUBLIC_GOOGLE_MAPS_API_KEY:
      process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || process.env.GOOGLE_MAPS_API_KEY || "",
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_CONTACT_EMAIL: process.env.NEXT_PUBLIC_CONTACT_EMAIL,
    NEXT_PUBLIC_CONTACT_PHONE: process.env.NEXT_PUBLIC_CONTACT_PHONE,
  },
};

export default withPWA(nextConfig);
