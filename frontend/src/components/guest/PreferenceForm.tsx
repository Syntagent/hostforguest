"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { guestGroupsApi, GuestGroup } from "@/lib/api";

interface PreferenceData {
  ageRange: string;
  interests: string[];
  mobilityLevel: string;
  budgetLevel: string;
  dietaryRestrictions: string[];
  specialRequests: string;
}

const INTEREST_CATEGORIES = {
  history: { icon: "🏛️", label: "History & Culture", color: "bg-purple-500" },
  nature: { icon: "🌿", label: "Nature & Outdoors", color: "bg-green-500" },
  food: { icon: "🍽️", label: "Food & Wine", color: "bg-orange-500" },
  adventure: { icon: "🏃", label: "Adventure & Sports", color: "bg-blue-500" },
  relaxation: { icon: "🧘", label: "Relaxation & Wellness", color: "bg-pink-500" },
  shopping: { icon: "🛍️", label: "Shopping & Markets", color: "bg-yellow-500" },
  nightlife: { icon: "🍷", label: "Nightlife & Entertainment", color: "bg-indigo-500" },
  photography: { icon: "📸", label: "Photography", color: "bg-teal-500" },
};

const DIETARY_OPTIONS = [
  "Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "Halal", "Kosher", "None"
];

export const PreferenceForm: React.FC = () => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guestGroup, setGuestGroup] = useState<GuestGroup | null>(null);
  const [formData, setFormData] = useState<PreferenceData>({
    ageRange: "adult",
    interests: [],
    mobilityLevel: "high",
    budgetLevel: "medium",
    dietaryRestrictions: [],
    specialRequests: "",
  });
  const router = useRouter();
  const searchParams = useSearchParams();
  const accessCode = searchParams.get("accessCode");

  useEffect(() => {
    if (accessCode) {
      loadGuestGroup();
    }
  }, [accessCode]);

  const loadGuestGroup = async () => {
    if (!accessCode) return;
    
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

  const handleInterestToggle = (interest: string) => {
    setFormData(prev => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter(i => i !== interest)
        : [...prev.interests, interest]
    }));
  };

  const handleDietaryToggle = (dietary: string) => {
    setFormData(prev => ({
      ...prev,
      dietaryRestrictions: prev.dietaryRestrictions.includes(dietary)
        ? prev.dietaryRestrictions.filter(d => d !== dietary)
        : [...prev.dietaryRestrictions, dietary]
    }));
  };

  const handleSubmit = async () => {
    if (!accessCode) return;
    
    setLoading(true);
    setError(null);

    try {
      // Update guest preference with detailed information
      const preferenceData = {
        guest_name: guestGroup?.group_name?.trim() || "Guest",
        age_category: formData.ageRange,
        personal_interests: formData.interests,
        dietary_needs: formData.dietaryRestrictions,
        mobility_notes: formData.mobilityLevel,
        cultural_interests: formData.interests.filter(i => ["history", "food"].includes(i)),
        food_interests: formData.interests.filter((i) => i === "food") as string[],
        language_preference: "en",
      };

      const response = await guestGroupsApi.addGuestPreference(accessCode, preferenceData);
      
      if (!response.success) {
        throw new Error(response.error || "Failed to save preferences");
      }

      // Redirect to guest dashboard
      router.push(`/guest/dashboard`);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save preferences");
    } finally {
      setLoading(false);
    }
  };

  const nextStep = () => setStep(prev => Math.min(prev + 1, 4));
  const prevStep = () => setStep(prev => Math.max(prev - 1, 1));

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
        className="w-full max-w-2xl"
      >
        <Card className="bg-white/10 backdrop-blur-sm border-white/20 text-white">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-bold text-white">
              Tell Us About Your Preferences
            </CardTitle>
            {guestGroup && (
              <p className="text-blue-100">
                Help us personalize your Croatian experience
              </p>
            )}
            
            {/* Progress indicator */}
            <div className="flex justify-center mt-4">
              {[1, 2, 3, 4].map((stepNumber) => (
                <div key={stepNumber} className="flex items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    stepNumber <= step 
                      ? "bg-blue-500 text-white" 
                      : "bg-white/20 text-blue-200"
                  }`}>
                    {stepNumber}
                  </div>
                  {stepNumber < 4 && (
                    <div className={`w-8 h-0.5 mx-2 ${
                      stepNumber < step ? "bg-blue-500" : "bg-white/20"
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            <AnimatePresence mode="wait">
              {step === 1 && (
                <motion.div
                  key="step1"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-6"
                >
                  <div>
                    <Label className="text-white font-medium text-lg mb-4 block">
                      What&apos;s your age range?
                    </Label>
                    <div className="grid grid-cols-2 gap-4">
                      {["child", "teen", "adult", "senior"].map((age) => (
                        <Button
                          key={age}
                          variant={formData.ageRange === age ? "primary" : "outline"}
                          onClick={() => setFormData(prev => ({ ...prev, ageRange: age }))}
                          className="h-16 text-lg capitalize"
                        >
                          {age}
                        </Button>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}

              {step === 2 && (
                <motion.div
                  key="step2"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-6"
                >
                  <div>
                    <Label className="text-white font-medium text-lg mb-4 block">
                      What interests you most? (Select all that apply)
                    </Label>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {Object.entries(INTEREST_CATEGORIES).map(([key, { icon, label, color }]) => (
                        <Button
                          key={key}
                          variant={formData.interests.includes(key) ? "primary" : "outline"}
                          onClick={() => handleInterestToggle(key)}
                          className="h-20 flex flex-col items-center justify-center space-y-2"
                        >
                          <span className="text-2xl">{icon}</span>
                          <span className="text-xs">{label}</span>
                        </Button>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}

              {step === 3 && (
                <motion.div
                  key="step3"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-6"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <Label className="text-white font-medium text-lg mb-4 block">
                        Mobility Level
                      </Label>
                      <div className="space-y-3">
                        {["high", "medium", "low"].map((level) => (
                          <Button
                            key={level}
                            variant={formData.mobilityLevel === level ? "primary" : "outline"}
                            onClick={() => setFormData(prev => ({ ...prev, mobilityLevel: level }))}
                            className="w-full justify-start capitalize"
                          >
                            {level} - {level === "high" ? "Very active" : level === "medium" ? "Moderate activity" : "Limited mobility"}
                          </Button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <Label className="text-white font-medium text-lg mb-4 block">
                        Budget Level
                      </Label>
                      <div className="space-y-3">
                        {["low", "medium", "high"].map((level) => (
                          <Button
                            key={level}
                            variant={formData.budgetLevel === level ? "primary" : "outline"}
                            onClick={() => setFormData(prev => ({ ...prev, budgetLevel: level }))}
                            className="w-full justify-start capitalize"
                          >
                            {level} - {level === "low" ? "Budget-friendly" : level === "medium" ? "Mid-range" : "Premium"}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div>
                    <Label className="text-white font-medium text-lg mb-4 block">
                      Dietary Restrictions (Select all that apply)
                    </Label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {DIETARY_OPTIONS.map((dietary) => (
                        <Button
                          key={dietary}
                          variant={formData.dietaryRestrictions.includes(dietary) ? "primary" : "outline"}
                          onClick={() => handleDietaryToggle(dietary)}
                          className="h-12 text-sm"
                        >
                          {dietary}
                        </Button>
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}

              {step === 4 && (
                <motion.div
                  key="step4"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-6"
                >
                  <div>
                    <Label className="text-white font-medium text-lg mb-4 block">
                      Special Requests or Notes
                    </Label>
                    <textarea
                      value={formData.specialRequests}
                      onChange={(e) => setFormData(prev => ({ ...prev, specialRequests: e.target.value }))}
                      placeholder="Any special requirements, accessibility needs, or specific interests..."
                      className="w-full h-32 bg-white/20 border border-white/30 text-white rounded-md px-3 py-2 placeholder:text-blue-200 resize-none"
                    />
                  </div>

                  <div className="bg-white/10 rounded-lg p-4">
                    <h3 className="text-white font-semibold mb-2">Summary</h3>
                    <div className="text-blue-100 text-sm space-y-1">
                      <p>Age: {formData.ageRange}</p>
                      <p>Interests: {formData.interests.join(", ") || "None selected"}</p>
                      <p>Mobility: {formData.mobilityLevel}</p>
                      <p>Budget: {formData.budgetLevel}</p>
                      <p>Dietary: {formData.dietaryRestrictions.join(", ") || "None"}</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {error && (
              <Alert variant="destructive" className="bg-red-500/20 border-red-400/30">
                <AlertDescription className="text-red-100">
                  {error}
                </AlertDescription>
              </Alert>
            )}

            <div className="flex justify-between mt-8">
              <Button
                variant="outline"
                onClick={prevStep}
                disabled={step === 1}
                className="text-white border-white/30 hover:bg-white/10"
              >
                Previous
              </Button>

              {step < 4 ? (
                <Button
                  onClick={nextStep}
                  className="bg-gradient-to-r from-blue-500 to-teal-500 hover:from-blue-600 hover:to-teal-600"
                >
                  Next
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="bg-gradient-to-r from-blue-500 to-teal-500 hover:from-blue-600 hover:to-teal-600"
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Saving...
                    </div>
                  ) : (
                    "Save Preferences & Continue"
                  )}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};
