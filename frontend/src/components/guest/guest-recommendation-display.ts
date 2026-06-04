import type { Recommendation } from "@/lib/api";

const HIDDEN_FACTOR_RE = /algorithm|request type|weights:\s*\{|season:\s*spring/i;

const QA_ATTRACTION_RE =
  /ben component|ben qa|full-component|full component qa|qa attraction|test attraction|slash-test|\bverify /i;

/** Hide host QA / test attractions from guest Discover and map. */
export function isGuestVisibleRecommendation(rec: Recommendation): boolean {
  const att = rec.attraction;
  if (!att) return true;
  const blob = `${att.name || ""} ${att.description || ""}`;
  return !QA_ATTRACTION_RE.test(blob);
}

/** Guest-facing chips only — hide internal scoring metadata. */
export function guestFacingFactors(rec: Recommendation): string[] {
  const raw = rec.personalization_factors || [];
  return raw
    .map((f) => String(f).trim())
    .filter((f) => f.length > 0 && f.length < 48 && !HIDDEN_FACTOR_RE.test(f))
    .slice(0, 4);
}

export function guestFacingReason(rec: Recommendation): string {
  const tip = rec.attraction?.host_personal_tip?.trim();
  if (tip && tip.length > 12 && !/qa|test|component/i.test(tip)) {
    return tip;
  }
  const reason = rec.reason?.trim();
  if (reason && !/special insights/i.test(reason)) {
    return reason;
  }
  const name = rec.attraction?.name?.trim() || "this place";
  const city = rec.attraction?.city?.trim() || "the area";
  return `Your host recommends ${name} while you stay in ${city}.`;
}
