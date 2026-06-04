"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useAuth } from "@/contexts/auth-context";
import { hostsApi } from "@/lib/api";
import {
  HOST_ACCESS_PROCEDURE,
  isHostProfileReady,
} from "@/lib/host-account-procedure";

const REMEMBER_EMAIL_KEY = "hfg_remember_email";

const contactEmail =
  process.env.NEXT_PUBLIC_CONTACT_EMAIL || "info@syntagent.com";

export function LoginClient() {
  const router = useRouter();
  const { login, user, loading: authLoading, error: authError, clearError } = useAuth();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [rememberEmail, setRememberEmail] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem(REMEMBER_EMAIL_KEY);
    if (saved) {
      setFormData((prev) => ({ ...prev, email: saved }));
    }
  }, []);

  useEffect(() => {
    if (!authLoading && user) {
      router.replace("/dashboard");
    }
  }, [authLoading, user, router]);

  const displayError = localError || authError;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    if (localError) setLocalError(null);
    if (authError) clearError();
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const persistEmail = () => {
    if (typeof window === "undefined") return;
    if (rememberEmail && formData.email.trim()) {
      localStorage.setItem(REMEMBER_EMAIL_KEY, formData.email.trim());
    } else {
      localStorage.removeItem(REMEMBER_EMAIL_KEY);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setLocalError(null);
    clearError();

    try {
      persistEmail();
      const result = await login(formData.email.trim(), formData.password);

      if (result.ok) {
        const profileRes = await hostsApi.getProfile();
        const ready = isHostProfileReady(
          profileRes.success ? profileRes.data : null
        );
        router.push(ready ? "/dashboard" : "/onboarding?from=login");
      } else {
        setLocalError(result.error);
      }
    } catch (error) {
      console.error("Login error:", error);
      setLocalError("Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (authLoading || user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-600 via-teal-600 to-green-600">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center text-white"
        >
          <motion.div
            className="mx-auto mb-4 h-10 w-10 rounded-full border-2 border-white border-t-transparent"
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
          />
          <p className="text-sm font-medium">
            {user ? "Opening dashboard…" : "Checking session…"}
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-teal-600 to-green-600 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Card className="shadow-2xl border-0 bg-white/95 backdrop-blur-sm">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 w-16 h-16 bg-gradient-to-br from-blue-500 to-teal-500 rounded-full flex items-center justify-center">
              <span className="text-2xl text-white" aria-hidden>
                🇭🇷
              </span>
            </div>
            <CardTitle className="text-2xl font-bold text-gray-900">Host sign in</CardTitle>
            <CardDescription className="text-gray-600">
              Access your Croatian hospitality dashboard
            </CardDescription>
          </CardHeader>

          <CardContent>
            <Alert className="mb-5 border-blue-200 bg-blue-50 text-blue-950">
              <AlertTitle className="text-blue-900">How host access works</AlertTitle>
              <AlertDescription>
                <ol className="mt-2 list-decimal space-y-2 pl-4 text-blue-900/90">
                  {HOST_ACCESS_PROCEDURE.map((item) => (
                    <li key={item.step}>
                      <span className="font-medium">{item.title}</span> {item.body}
                    </li>
                  ))}
                </ol>
              </AlertDescription>
            </Alert>

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {displayError && (
                <Alert variant="destructive">
                  <AlertDescription>{displayError}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  type="email"
                  id="email"
                  name="email"
                  autoComplete="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  placeholder="you@example.com"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <a
                    href={`mailto:${contactEmail}?subject=HostForGuest%20password%20help`}
                    className="text-xs font-medium text-blue-600 hover:text-blue-500"
                  >
                    Forgot password?
                  </a>
                </div>
                <div className="relative">
                  <Input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    name="password"
                    autoComplete="current-password"
                    value={formData.password}
                    onChange={handleInputChange}
                    required
                    placeholder="Your password"
                    className="pr-10"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={rememberEmail}
                  onChange={(e) => setRememberEmail(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                Remember me on this device
              </label>

              <Button
                type="submit"
                className="w-full bg-gradient-to-r from-blue-600 to-teal-600 hover:from-blue-700 hover:to-teal-700"
                disabled={loading}
              >
                {loading ? "Signing in…" : "Sign in"}
              </Button>

            </form>

            <p className="mt-6 text-center text-sm text-gray-600">
              <span className="font-medium text-gray-800">New host?</span>{" "}
              <Link
                href="/onboarding"
                className="font-medium text-blue-600 hover:text-blue-500"
              >
                Create your profile
              </Link>
              <span className="block mt-1 text-xs text-gray-500">
                Required before you can sign in — creates your account and property setup.
              </span>
            </p>

            <p className="mt-4 text-center text-xs text-gray-500">HostForGuest by Syntagent</p>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
