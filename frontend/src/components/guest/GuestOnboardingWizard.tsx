"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Check, ChevronLeft, ChevronRight, KeyRound, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { guestGroupsApi, GuestGroup } from "@/lib/api";

const INTEREST_OPTIONS: Record<string, { icon: string; label: string }> = {
  history: { icon: "🏛️", label: "History & culture" },
  nature: { icon: "🌿", label: "Nature & outdoors" },
  food: { icon: "🍽️", label: "Food & wine" },
  adventure: { icon: "🏃", label: "Adventure & sports" },
  relaxation: { icon: "🧘", label: "Relaxation" },
  shopping: { icon: "🛍️", label: "Shopping & markets" },
  nightlife: { icon: "🍷", label: "Nightlife" },
  photography: { icon: "📸", label: "Photography" },
};

const DIETARY_OPTIONS = [
  "Vegetarian",
  "Vegan",
  "Gluten-free",
  "Dairy-free",
  "Halal",
  "Kosher",
  "None",
];

const AGE_GROUP_KEYS = ["child", "teen", "adult", "senior"] as const;
type AgeGroupKey = (typeof AGE_GROUP_KEYS)[number];

const AGE_LABELS: Record<AgeGroupKey, string> = {
  child: "Child",
  teen: "Teen",
  adult: "Adult",
  senior: "Senior",
};

const AGE_GROUP_ORDER: Record<AgeGroupKey, number> = {
  child: 0,
  teen: 1,
  adult: 2,
  senior: 3,
};

function sortAgeGroups(keys: AgeGroupKey[]): AgeGroupKey[] {
  return [...keys].sort((a, b) => AGE_GROUP_ORDER[a] - AGE_GROUP_ORDER[b]);
}

function ageGroupsToApiString(keys: AgeGroupKey[]): string {
  return sortAgeGroups(keys).join(",");
}

function ageGroupsSummary(keys: AgeGroupKey[]): string {
  return sortAgeGroups(keys)
    .map((k) => AGE_LABELS[k])
    .join(", ");
}

const MOBILITY_LABELS: Record<string, string> = {
  high: "Active (long walks OK)",
  medium: "Moderate",
  low: "Limited (fewer stairs / shorter walks)",
};

const BUDGET_LABELS: Record<string, string> = {
  low: "Budget-friendly",
  medium: "Balanced",
  high: "Comfort / premium",
};

const STEP_TITLES = [
  "About you",
  "Age",
  "Interests",
  "Comfort & food",
  "Review",
];

export interface GuestOnboardingWizardProps {
  accessCode: string;
}

/**
 * Full guest flow: who you are → travel preferences → one POST to the API.
 * After success, sends the guest to /guest/{code} (main app).
 */
export const GuestOnboardingWizard: React.FC<GuestOnboardingWizardProps> = ({
  accessCode,
}) => {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [loadGroup, setLoadGroup] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [guestGroup, setGuestGroup] = useState<GuestGroup | null>(null);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [language, setLanguage] = useState("en");
  const [termsAccepted, setTermsAccepted] = useState(false);

  const [ageGroups, setAgeGroups] = useState<AgeGroupKey[]>(["adult"]);
  const [interests, setInterests] = useState<string[]>([]);
  const [mobilityLevel, setMobilityLevel] = useState("high");
  const [budgetLevel, setBudgetLevel] = useState("medium");
  const [dietary, setDietary] = useState<string[]>([]);
  const [specialRequests, setSpecialRequests] = useState("");

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [step]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await guestGroupsApi.getByAccessCode(accessCode);
        if (cancelled) return;
        if (res.success && res.data) {
          setGuestGroup(res.data);
        } else {
          setError(res.error || "Invalid or expired access code");
        }
      } catch {
        if (!cancelled) setError("Could not load your group. Check your connection.");
      } finally {
        if (!cancelled) setLoadGroup(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [accessCode]);

  const toggleInterest = (key: string) => {
    setInterests((prev) =>
      prev.includes(key) ? prev.filter((x) => x !== key) : [...prev, key]
    );
  };

  const toggleDietary = (d: string) => {
    setDietary((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
    );
  };

  const toggleAgeGroup = (key: AgeGroupKey) => {
    setAgeGroups((prev) =>
      prev.includes(key) ? prev.filter((x) => x !== key) : [...prev, key]
    );
  };

  const buildMobilityNotes = () => {
    const lines = [
      `Email: ${email.trim()}`,
      phone.trim() ? `Phone: ${phone.trim()}` : null,
      `Mobility: ${mobilityLevel}`,
      `Budget: ${budgetLevel}`,
    ].filter(Boolean) as string[];
    if (specialRequests.trim()) {
      lines.push("---", specialRequests.trim());
    }
    return lines.join("\n");
  };

  const interestSummary = () =>
    interests
      .map((k) => INTEREST_OPTIONS[k]?.label || k)
      .join(", ") || "—";

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const guest_name = `${firstName.trim()} ${lastName.trim()}`.trim();
      const cultural = interests.filter((i) =>
        ["history", "photography", "shopping"].includes(i)
      );
      const food_interests = interests.includes("food") ? ["food"] : [];

      const res = await guestGroupsApi.addGuestPreference(accessCode, {
        guest_name,
        age_category: ageGroupsToApiString(ageGroups),
        personal_interests: interests,
        dietary_needs: dietary.filter((x) => x !== "None"),
        mobility_notes: buildMobilityNotes(),
        language_preference: language,
        cultural_interests: cultural,
        food_interests,
      });

      if (!res.success) {
        throw new Error(res.error || "Could not save your profile");
      }

      if (typeof window !== "undefined") {
        localStorage.setItem("guest_access_code", accessCode);
      }
      router.push(`/guest/${accessCode}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const next = () => setStep((s) => Math.min(s + 1, 5));
  const prev = () => setStep((s) => Math.max(s - 1, 1));

  if (loadGroup) {
    return (
      <div
        className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-white"
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <Loader2 className="h-10 w-10 animate-spin text-white/90" aria-hidden />
        <div className="text-center">
          <p className="text-lg font-medium">Checking your invitation…</p>
          <p className="mt-1 text-sm text-blue-100">
            Hang on while we connect to your host&apos;s group.
          </p>
        </div>
      </div>
    );
  }

  if (error && !guestGroup) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="mx-auto w-full max-w-md space-y-5 rounded-3xl border border-white/30 bg-white p-8 text-center text-slate-900 shadow-xl">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
            <KeyRound className="h-7 w-7 text-primary" aria-hidden />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-900">We couldn&apos;t open that code</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{error}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
            <Button
              type="button"
              className="w-full sm:w-auto"
              onClick={() => router.push("/guest/join")}
            >
              Try another code
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const progressPercent = Math.round((step / 5) * 100);

  return (
    <div className="relative flex min-h-screen w-full max-w-full flex-col items-center overflow-x-hidden px-3 pb-24 pt-3 sm:justify-center sm:px-6 sm:pb-12 sm:pt-10">
      <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-30 [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0.35))]" aria-hidden />

      <p className="relative z-10 mb-2 text-center text-xs text-blue-100 sm:mb-4">
        <Link
          href="/guest/join"
          className="underline decoration-white/40 underline-offset-2 transition-colors hover:text-white"
        >
          Wrong code? Enter a different one
        </Link>
      </p>

      <div className="relative z-10 w-full max-w-2xl">
        <article className="overflow-hidden rounded-2xl border border-white/25 bg-white/[0.14] text-white shadow-[0_25px_50px_-12px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:rounded-3xl">
          <div className="flex flex-col space-y-2 p-4 text-center sm:space-y-4 sm:p-6 md:p-7">
            <h3 className="text-xl font-bold leading-tight tracking-tight sm:text-3xl">
              Set up your stay
            </h3>
            {guestGroup && (
              <p className="text-pretty text-xs text-blue-100 sm:text-base">
                <span className="font-medium text-white">
                  {guestGroup.group_name || "Your group"}
                </span>
                {" — "}
                A few quick questions help your host tailor tips and places for you.
              </p>
            )}
            <div
              className="mx-auto w-full max-w-xs pt-1"
              role="progressbar"
              aria-valuenow={progressPercent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Step ${step} of 5`}
            >
              <div className="mb-1.5 flex justify-center gap-1.5 sm:mb-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <div
                    key={n}
                    className={`h-2 flex-1 max-w-10 rounded-full transition-colors duration-300 ${
                      n <= step ? "bg-white" : "bg-white/25"
                    }`}
                  />
                ))}
              </div>
              <p className="text-xs text-blue-200">
                Step {step} of 5 — {STEP_TITLES[step - 1]}
              </p>
            </div>
          </div>
          <div className="px-3 pb-3 pt-0 sm:px-6 sm:pb-6 md:px-7 md:pb-7">
              {step === 1 && (
                <div key="s1" className="space-y-3 sm:space-y-4">
                  <div className="grid grid-cols-2 gap-2 sm:gap-3">
                    <div>
                      <Label htmlFor="g-first" className="text-white">
                        First name *
                      </Label>
                      <Input
                        id="g-first"
                        name="given-name"
                        autoComplete="given-name"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        className="mt-1 min-h-10 rounded-xl border-white/30 bg-white/20 text-white placeholder:text-blue-200/80 sm:mt-1.5 sm:min-h-11"
                        placeholder="Ivan"
                      />
                    </div>
                    <div>
                      <Label htmlFor="g-last" className="text-white">
                        Last name *
                      </Label>
                      <Input
                        id="g-last"
                        name="family-name"
                        autoComplete="family-name"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        className="mt-1 min-h-10 rounded-xl border-white/30 bg-white/20 text-white placeholder:text-blue-200/80 sm:mt-1.5 sm:min-h-11"
                        placeholder="Horvat"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="g-email" className="text-white">
                      Email *
                    </Label>
                    <Input
                      id="g-email"
                      type="email"
                      name="email"
                      autoComplete="email"
                      inputMode="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    className="mt-1 min-h-10 rounded-xl border-white/30 bg-white/20 text-white placeholder:text-blue-200/80 sm:mt-1.5 sm:min-h-11"
                      placeholder="you@example.com"
                    />
                  </div>
                  <div>
                    <Label htmlFor="g-phone" className="text-white">
                      Phone (optional)
                    </Label>
                    <Input
                      id="g-phone"
                      type="tel"
                      name="tel"
                      autoComplete="tel"
                      inputMode="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="mt-1 min-h-10 rounded-xl border-white/30 bg-white/20 text-white placeholder:text-blue-200/80 sm:mt-1.5 sm:min-h-11"
                      placeholder="+385 …"
                    />
                  </div>
                  <div>
                    <Label htmlFor="g-lang" className="text-white">
                      Preferred language
                    </Label>
                    <select
                      id="g-lang"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="mt-1 min-h-10 w-full rounded-xl border border-white/30 bg-white/95 px-3 py-2 text-sm text-gray-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-white/50 sm:mt-1.5 sm:min-h-11"
                    >
                      <option value="en">English</option>
                      <option value="hr">Hrvatski</option>
                      <option value="de">Deutsch</option>
                      <option value="it">Italiano</option>
                    </select>
                  </div>
                  <label className="flex cursor-pointer items-start gap-2 rounded-xl bg-white/5 p-2.5 text-xs leading-snug text-white sm:gap-3 sm:p-3 sm:text-sm">
                    <input
                      type="checkbox"
                      checked={termsAccepted}
                      onChange={(e) => setTermsAccepted(e.target.checked)}
                      className="mt-0.5 h-4 w-4 shrink-0 rounded border-white/40 text-blue-600 focus:ring-white/50"
                    />
                    <span>
                      I agree my host may use these details to personalize my stay
                      (as agreed with your host).
                    </span>
                  </label>
                </div>
              )}

              {step === 2 && (
                <div key="s2" className="space-y-3 sm:space-y-4">
                  <Label className="text-sm font-medium text-white sm:text-base">
                    Who is traveling? (age groups)
                  </Label>
                  <p className="text-xs text-blue-100 sm:text-sm">
                    Select all that apply — we use this to tune walking distances and activity
                    suggestions for everyone in your group.
                  </p>
                  <div className="grid grid-cols-2 gap-2 sm:gap-3">
                    {AGE_GROUP_KEYS.map((a) => {
                      const selected = ageGroups.includes(a);
                      return (
                        <Button
                          key={a}
                          type="button"
                          variant={selected ? "primary" : "outline"}
                          aria-pressed={selected}
                          onClick={() => toggleAgeGroup(a)}
                          className="h-auto min-h-11 rounded-xl py-2 text-sm sm:min-h-14 sm:py-3"
                        >
                          {AGE_LABELS[a]}
                        </Button>
                      );
                    })}
                  </div>
                </div>
              )}

              {step === 3 && (
                <div key="s3" className="space-y-3 sm:space-y-4">
                  <Label className="text-sm font-medium text-white sm:text-base">
                    What are you into?
                  </Label>
                  <p className="text-xs text-blue-100 sm:text-sm">Pick anything that sounds fun — no wrong answers.</p>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {Object.entries(INTEREST_OPTIONS).map(([key, v]) => (
                      <Button
                        key={key}
                        type="button"
                        variant={interests.includes(key) ? "primary" : "outline"}
                        onClick={() => toggleInterest(key)}
                        className="flex h-auto min-h-14 flex-col gap-0.5 rounded-xl py-2 sm:min-h-[4.25rem] sm:gap-1 sm:py-2.5"
                      >
                        <span className="text-base sm:text-lg" aria-hidden>
                          {v.icon}
                        </span>
                        <span className="text-center text-[11px] font-medium leading-tight sm:text-xs">
                          {v.label}
                        </span>
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {step === 4 && (
                <div
                  key="s4"
                  className="max-h-[min(58vh,28rem)] space-y-4 overflow-y-auto pr-1 sm:space-y-6"
                >
                  <div>
                    <Label className="text-white">Walking & mobility</Label>
                    <p className="mb-2 text-xs text-blue-200">
                      Helps avoid routes with too many stairs or long hikes.
                    </p>
                    <div className="space-y-2">
                      {(
                        [
                          ["high", "Active — long walks OK"],
                          ["medium", "Moderate pace"],
                          ["low", "Limited — shorter walks, fewer stairs"],
                        ] as const
                      ).map(([v, label]) => (
                        <Button
                          key={v}
                          type="button"
                          variant={mobilityLevel === v ? "primary" : "outline"}
                          className="h-auto min-h-10 w-full justify-start whitespace-normal rounded-xl text-left text-sm sm:min-h-12"
                          onClick={() => setMobilityLevel(v)}
                        >
                          {label}
                        </Button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <Label className="text-white">Budget for outings</Label>
                    <div className="mt-2 grid grid-cols-3 gap-1.5 sm:gap-2">
                      {(["low", "medium", "high"] as const).map((b) => (
                        <Button
                          key={b}
                          type="button"
                          variant={budgetLevel === b ? "primary" : "outline"}
                          className="min-h-10 rounded-xl px-2 capitalize sm:min-h-11"
                          onClick={() => setBudgetLevel(b)}
                        >
                          {b}
                        </Button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <Label className="text-white">Dietary needs</Label>
                    <div className="mt-2 flex gap-2 overflow-x-auto pb-1 sm:flex-wrap sm:overflow-visible sm:pb-0">
                      {DIETARY_OPTIONS.map((d) => (
                        <Button
                          key={d}
                          type="button"
                          size="sm"
                          variant={dietary.includes(d) ? "primary" : "outline"}
                          onClick={() => toggleDietary(d)}
                          className="shrink-0 rounded-full"
                        >
                          {d}
                        </Button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="g-notes" className="text-white">
                      Anything else? (optional)
                    </Label>
                    <textarea
                      id="g-notes"
                      value={specialRequests}
                      onChange={(e) => setSpecialRequests(e.target.value)}
                      rows={2}
                      className="mt-1.5 w-full resize-none rounded-xl border border-white/30 bg-white/20 px-3 py-2 text-sm text-white placeholder:text-blue-200/80 focus:outline-none focus:ring-2 focus:ring-white/40"
                      placeholder="Allergies, accessibility, kids, celebration…"
                    />
                  </div>
                </div>
              )}

              {step === 5 && (
                <div
                  key="s5"
                  className="space-y-2 rounded-2xl bg-white/10 p-3 text-sm text-blue-100 sm:space-y-3 sm:p-4"
                >
                  <p className="border-b border-white/10 pb-2 text-xs font-medium uppercase tracking-wide text-blue-200">
                    Summary
                  </p>
                  <p>
                    <span className="font-medium text-white">Name:</span>{" "}
                    {firstName} {lastName}
                  </p>
                  <p>
                    <span className="font-medium text-white">Email:</span> {email}
                  </p>
                  {phone.trim() ? (
                    <p>
                      <span className="font-medium text-white">Phone:</span> {phone}
                    </p>
                  ) : null}
                  <p>
                    <span className="font-medium text-white">Age groups:</span>{" "}
                    {ageGroupsSummary(ageGroups)}
                  </p>
                  <p>
                    <span className="font-medium text-white">Interests:</span>{" "}
                    {interestSummary()}
                  </p>
                  <p>
                    <span className="font-medium text-white">Mobility:</span>{" "}
                    {MOBILITY_LABELS[mobilityLevel] ?? mobilityLevel}
                  </p>
                  <p>
                    <span className="font-medium text-white">Budget:</span>{" "}
                    {BUDGET_LABELS[budgetLevel] ?? budgetLevel}
                  </p>
                  <p>
                    <span className="font-medium text-white">Diet:</span>{" "}
                    {dietary.filter((x) => x !== "None").join(", ") || "—"}
                  </p>
                </div>
              )}

            {error && guestGroup ? (
              <Alert className="mt-4 rounded-xl border-red-400/40 bg-red-500/20">
                <AlertDescription className="text-red-50">{error}</AlertDescription>
              </Alert>
            ) : null}

            <div className="sticky bottom-0 -mx-3 mt-4 flex flex-row gap-2 border-t border-white/10 bg-slate-950/35 px-3 py-3 backdrop-blur-md sm:static sm:mx-0 sm:mt-8 sm:gap-3 sm:bg-transparent sm:px-0 sm:pt-6 sm:backdrop-blur-0">
              <Button
                type="button"
                variant="outline"
                className="min-h-10 flex-1 !border-white/55 !bg-white/10 px-3 text-white shadow-none backdrop-blur-sm hover:!bg-white/20 hover:!text-white focus-visible:ring-white/40 disabled:!border-white/20 disabled:!bg-white/5 disabled:!text-white/45 sm:w-auto sm:flex-none"
                disabled={step === 1}
                onClick={prev}
              >
                <ChevronLeft className="h-4 w-4" />
                <span className="hidden sm:inline">Back</span>
              </Button>
              {step < 5 ? (
                <Button
                  type="button"
                  className="min-h-10 flex-[2] px-3 sm:w-auto sm:flex-none"
                  onClick={() => {
                    if (step === 1) {
                      if (!firstName.trim() || !lastName.trim() || !email.trim()) {
                        setError("Please add your first name, last name, and email.");
                        return;
                      }
                      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
                        setError("Please enter a valid email address.");
                        return;
                      }
                      if (!termsAccepted) {
                        setError("Please tick the box to continue.");
                        return;
                      }
                      setError(null);
                    }
                    if (step === 2) {
                      if (ageGroups.length === 0) {
                        setError("Select at least one age group.");
                        return;
                      }
                      setError(null);
                    }
                    next();
                  }}
                >
                  Continue
                  <ChevronRight className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  type="button"
                  className="min-h-10 flex-[2] px-3 sm:w-auto sm:flex-none"
                  disabled={loading}
                  onClick={handleSubmit}
                >
                  {loading ? (
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      Saving…
                    </span>
                  ) : (
                    <>
                      <Check className="h-4 w-4" />
                      Open guide
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </article>
      </div>
    </div>
  );
};
