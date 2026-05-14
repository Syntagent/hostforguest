import HomeClient from "./home-client";

/** Avoid flaky static prerender of the marketing shell (framer-motion / client graph). */
export const dynamic = "force-dynamic";

export default function HomePage() {
  return <HomeClient />;
}
