"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { guestGroupsApi } from "@/lib/api";

export const AccessCodeForm: React.FC = () => {
  const [accessCode, setAccessCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Validate access code format
      if (!accessCode.trim()) {
        throw new Error("Please enter your access code");
      }

      if (accessCode.length < 6) {
        throw new Error("Access code must be at least 6 characters");
      }

      // Test access code with API
      const response = await guestGroupsApi.getByAccessCode(accessCode.trim());
      
      if (!response.success) {
        throw new Error(response.error || "Invalid access code");
      }

      // Profile + preferences first, then main guest app
      router.push(`/guest/setup/${accessCode.trim()}`);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to validate access code");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Card className="bg-white/10 backdrop-blur-sm border-white/20 text-white">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-white">
            Enter Your Access Code
          </CardTitle>
          <p className="text-pretty text-blue-100">
            Enter the code your host sent you. Next, you&apos;ll add your details and preferences so
            recommendations match your trip.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="accessCode" className="text-white font-medium">
                Access Code
              </Label>
              <Input
                id="accessCode"
                type="text"
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value.toUpperCase())}
                placeholder="YOUR-CODE"
                spellCheck={false}
                autoCapitalize="characters"
                className="border-white/30 bg-white/20 text-center font-mono text-lg tracking-[0.2em] text-white placeholder:text-blue-200/70 placeholder:tracking-normal focus:border-white/50"
                disabled={loading}
                autoComplete="off"
                autoFocus
                aria-invalid={error ? "true" : "false"}
                aria-describedby={
                  error ? "accessCode-hint accessCode-error" : "accessCode-hint"
                }
              />
              <p id="accessCode-hint" className="text-xs text-blue-200">
                Example: ABC123 or similar code from your host
              </p>
            </div>

            {error && (
              <div className="animate-in fade-in duration-200">
                <Alert variant="destructive" className="bg-red-500/20 border-red-400/30">
                  <AlertDescription id="accessCode-error" className="text-red-100">
                    {error}
                  </AlertDescription>
                </Alert>
              </div>
            )}

            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-blue-500 to-teal-500 hover:from-blue-600 hover:to-teal-600 text-white font-semibold py-3"
              disabled={loading || !accessCode.trim()}
              aria-busy={loading}
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <div
                    className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
                    aria-hidden
                  />
                  Checking your code…
                </div>
              ) : (
                "Continue"
              )}
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-white/20">
            <p className="text-center text-blue-200 text-sm">
              Don&apos;t have an access code?{" "}
              <span className="text-white font-medium">
                Contact your Croatian host
              </span>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
