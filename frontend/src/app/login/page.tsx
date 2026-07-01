import { headers } from "next/headers";
import { LoginClient } from "./login-client";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function LoginPage() {
  await headers();
  return <LoginClient />;
}
