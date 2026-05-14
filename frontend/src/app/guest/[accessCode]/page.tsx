import { GuestInterfaceClient } from "@/components/guest/guest-interface-client";
import { notFound } from "next/navigation";

type AccessParams = { accessCode: string };

function isThenable(v: unknown): v is Promise<AccessParams> {
  return (
    v != null &&
    typeof (v as Promise<unknown>).then === "function"
  );
}

export default async function GuestPage({
  params,
}: {
  params: Promise<AccessParams>;
}) {
  const resolved = isThenable(params) ? await params : (params as AccessParams);
  const raw = resolved?.accessCode;
  const accessCode = typeof raw === "string" ? raw.trim() : "";
  if (!accessCode) {
    notFound();
  }

  return <GuestInterfaceClient accessCode={accessCode} />;
}
