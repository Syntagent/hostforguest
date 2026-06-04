import type { Host, HostProfile } from "@/lib/api";

const PLACEHOLDER_FRAGMENTS = [
  "unknown",
  "to be updated",
  "address not specified",
  "city not set",
  "not set",
];

function isPlaceholder(value: string | undefined | null): boolean {
  const v = (value ?? "").trim().toLowerCase();
  if (!v) return true;
  return PLACEHOLDER_FRAGMENTS.some((p) => v.includes(p));
}

/** True when the host finished onboarding / has real property details for the dashboard. */
export function isHostProfileReady(
  profile: HostProfile | null | undefined,
  host?: Host | null
): boolean {
  if (profile?.onboarding_completed) return true;

  const city = profile?.city ?? host?.city;
  const address = profile?.address ?? host?.address;

  if (isPlaceholder(city) || isPlaceholder(address)) return false;
  return Boolean(city?.trim() && address?.trim());
}

export const HOST_ACCESS_PROCEDURE = [
  {
    step: 1,
    title: "First time here?",
    body: "Use Create your profile (onboarding). That registers your host account and your property details in one flow.",
  },
  {
    step: 2,
    title: "Already registered?",
    body: "Sign in with the email and password you chose during onboarding.",
  },
  {
    step: 3,
    title: "Sign in not working?",
    body: "You need a host account first. Sign in only works after onboarding — it does not create an account by itself.",
  },
] as const;
