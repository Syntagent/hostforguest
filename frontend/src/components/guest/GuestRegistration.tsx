"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { guestGroupsApi, GuestGroup } from "@/lib/api";

interface GuestRegistrationProps {
  accessCode: string;
}

interface RegistrationData {
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  languagePreference: string;
  termsAccepted: boolean;
}

export const GuestRegistration: React.FC<GuestRegistrationProps> = ({ accessCode }) => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guestGroup, setGuestGroup] = useState<GuestGroup | null>(null);
  const [formData, setFormData] = useState<RegistrationData>({
    firstName: "",
    lastName: "",
    email: "",
    phone: "",
    languagePreference: "en",
    termsAccepted: false,
  });
  const router = useRouter();

  useEffect(() => {
    loadGuestGroup();
  }, [accessCode]);

  const loadGuestGroup = async () => {
    try {
      const response = await guestGroupsApi.getByAccessCode(accessCode);
      if (response.success && response.data) {
        setGuestGroup(response.data);
      } else {
        setError("Invalid access code");
      }
    } catch (err) {
      setError("Failed to load group information");
    }
  };

  const handleInputChange = (field: keyof RegistrationData, value: string | boolean) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Validate form data
      if (!formData.firstName.trim() || !formData.lastName.trim() || !formData.email.trim()) {
        throw new Error("Please fill in all required fields");
      }

      if (!formData.termsAccepted) {
        throw new Error("Please accept the terms and conditions");
      }

      // Add guest preference to the group
      const preferenceData = {
        guest_name: `${formData.firstName} ${formData.lastName}`,
        age_category: "adult", // Default, can be updated later
        personal_interests: [],
        dietary_needs: [],
        cultural_interests: [],
        food_interests: [],
        language_preference: formData.languagePreference,
      };

      const response = await guestGroupsApi.addGuestPreference(accessCode, preferenceData);
      
      if (!response.success) {
        throw new Error(response.error || "Failed to register guest");
      }

      // Redirect to preferences page
      router.push(`/guest/preferences?accessCode=${accessCode}`);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  if (error && !guestGroup) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md mx-auto bg-white/10 backdrop-blur-sm border-white/20 text-white">
          <CardContent className="text-center p-6">
            <div className="text-6xl mb-4">🚫</div>
            <h2 className="text-xl font-bold mb-2">Access Denied</h2>
            <p className="text-blue-200 mb-4">{error}</p>
            <Button onClick={() => router.push("/guest/join")}>
              Try Different Code
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Card className="bg-white/10 backdrop-blur-sm border-white/20 text-white">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-bold text-white">
              Join Your Croatian Adventure
            </CardTitle>
            {guestGroup && (
              <p className="text-blue-100">
                Welcome to <span className="font-semibold">{guestGroup.group_name}</span>
              </p>
            )}
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName" className="text-white font-medium">
                    First Name *
                  </Label>
                  <Input
                    id="firstName"
                    type="text"
                    value={formData.firstName}
                    onChange={(e) => handleInputChange("firstName", e.target.value)}
                    className="bg-white/20 border-white/30 text-white placeholder:text-blue-200"
                    placeholder="Your first name"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName" className="text-white font-medium">
                    Last Name *
                  </Label>
                  <Input
                    id="lastName"
                    type="text"
                    value={formData.lastName}
                    onChange={(e) => handleInputChange("lastName", e.target.value)}
                    className="bg-white/20 border-white/30 text-white placeholder:text-blue-200"
                    placeholder="Your last name"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-white font-medium">
                  Email Address *
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange("email", e.target.value)}
                  className="bg-white/20 border-white/30 text-white placeholder:text-blue-200"
                  placeholder="your.email@example.com"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone" className="text-white font-medium">
                  Phone Number (Optional)
                </Label>
                <Input
                  id="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => handleInputChange("phone", e.target.value)}
                  className="bg-white/20 border-white/30 text-white placeholder:text-blue-200"
                  placeholder="+1 (555) 123-4567"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="language" className="text-white font-medium">
                  Language Preference
                </Label>
                <select
                  id="language"
                  value={formData.languagePreference}
                  onChange={(e) => handleInputChange("languagePreference", e.target.value)}
                  className="w-full bg-white/20 border border-white/30 text-white rounded-md px-3 py-2 focus:border-white/50"
                >
                  <option value="en">English</option>
                  <option value="hr">Hrvatski (Croatian)</option>
                  <option value="de">Deutsch (German)</option>
                  <option value="it">Italiano (Italian)</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="flex items-center space-x-2 text-white">
                  <input
                    type="checkbox"
                    checked={formData.termsAccepted}
                    onChange={(e) => handleInputChange("termsAccepted", e.target.checked)}
                    className="rounded border-white/30 bg-white/20"
                    required
                  />
                  <span className="text-sm">
                    I accept the{" "}
                    <span className="underline">terms and conditions</span> and{" "}
                    <span className="underline">privacy policy</span>
                  </span>
                </label>
              </div>

              {error && (
                <Alert variant="destructive" className="bg-red-500/20 border-red-400/30">
                  <AlertDescription className="text-red-100">
                    {error}
                  </AlertDescription>
                </Alert>
              )}

              <Button
                type="submit"
                className="w-full bg-gradient-to-r from-blue-500 to-teal-500 hover:from-blue-600 hover:to-teal-600 text-white font-semibold py-3"
                disabled={loading}
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    Joining...
                  </div>
                ) : (
                  "Join Group & Continue"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};
