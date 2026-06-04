"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { HeroSection } from "@/components/ui/hero-section";
import { BentoGrid } from "@/components/ui/bento-grid";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FeatureSection } from "@/components/ui/feature-section";
import { cn } from "@/lib/utils";
import { onboardingApi, authApi, API_BASE_URL, hostsApi } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

interface OnboardingStep {
  id: number;
  title: string;
  description: string;
  component: React.ComponentType<any>;
}

interface HostOnboardingProps {
  className?: string;
  onComplete?: (hostData: any) => void;
  /** When true, always show registration even if a session exists (e2e / new host signup). */
  forceRegistration?: boolean;
}

export const HostOnboarding: React.FC<HostOnboardingProps> = ({
  className,
  onComplete,
  forceRegistration = false,
}) => {
  const { user: currentHost, loading: authLoading } = useAuth();
  const [currentStep, setCurrentStep] = useState(1); // Skip welcome step, start at registration
  const [hostData, setHostData] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [authStepApplied, setAuthStepApplied] = useState(false);

  // Signed-in hosts already have an account — skip registration, go to property profile.
  React.useEffect(() => {
    if (forceRegistration || authLoading || !currentHost || authStepApplied) return;
    setHostData((prev: Record<string, unknown>) => ({
      ...prev,
      full_name: currentHost.full_name,
      email: currentHost.email,
      first_name: currentHost.first_name,
      last_name: currentHost.last_name,
      registered: true,
      host_id: currentHost.id,
    }));
    setCurrentStep(2);
    setAuthStepApplied(true);
  }, [forceRegistration, authLoading, currentHost, authStepApplied]);

  const steps: OnboardingStep[] = [
    {
      id: 0,
      title: "Welcome to Croatian Hospitality",
      description: "Join the platform that connects Croatian hosts with international guests.",
      component: WelcomeStep,
    },
    {
      id: 1,
      title: "Create Your Account",
      description: "Register with your email and create a secure password.",
      component: RegistrationStep,
    },
    {
      id: 2,
      title: "Basic Information",
      description: "Tell us about your property and location.",
      component: BasicInfoStep,
    },
    {
      id: 3,
      title: "AI Profile Generation",
      description: "Let AI help create your authentic host profile.",
      component: AIProfileStep,
    },
    {
      id: 4,
      title: "Local Attractions",
      description: "Share your knowledge of local hidden gems.",
      component: AttractionsStep,
    },
    {
      id: 5,
      title: "Review & Launch",
      description: "Review your profile and start welcoming guests.",
      component: ReviewStep,
    },
  ];

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const updateHostData = (data: any) => {
    setHostData({ ...hostData, ...data });
  };

  const completeOnboarding = async () => {
    console.log('🚀 Starting onboarding completion...');
    console.log('Host data to save:', hostData);
    setLoading(true);
    try {
      // Call the backend API to complete onboarding
      console.log('💾 Saving host data to backend...');

      // Format data for backend API
      const onboardingData = {
        city: hostData.city || '',
        region: hostData.region || 'Istria',
        address: hostData.location || hostData.address || '',
        property_name: hostData.business_name || '',
        property_type: hostData.property_type || 'apartment',
        coordinates: hostData.coordinates || null,
        interests: hostData.specialties || hostData.interests || [],
        languages: hostData.languages || [],
        local_experience: hostData.local_experience || null,
        preferred_guests: hostData.preferred_guests || [],
        location_story: hostData.location_story || '',
        knowledge_level: hostData.knowledge_level || 'intermediate'
      };

      console.log('📦 Formatted onboarding data:', onboardingData);
      const response = await onboardingApi.completeOnboarding(onboardingData);

      if (response.success) {
        console.log('✅ Host data saved successfully');

        if (onComplete) {
          console.log('📞 Calling onComplete callback...');
          onComplete(hostData);
        } else {
          console.warn('⚠️ No onComplete callback provided');
        }
      } else {
        console.error('❌ Onboarding completion failed:', response.error);
        alert('Failed to complete onboarding: ' + (response.error || 'Unknown error'));
        return;
      }
    } catch (error) {
      console.error('❌ Error completing onboarding:', error);
      alert('Error completing onboarding: ' + (error instanceof Error ? error.message : 'Unknown error'));
      // Don't redirect on error, stay on the review step
      return;
    } finally {
      setLoading(false);
    }
  };

  const CurrentStepComponent = steps[currentStep].component;

  return (
    <div className={cn("min-h-screen bg-gray-50", className)}>
      {/* Progress Bar */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Host Onboarding
            </h2>
            <span className="text-sm text-gray-600">
              Step {currentStep + 1} of {steps.length}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <motion.div
              className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full"
              initial={{ width: "0%" }}
              animate={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>
      </div>

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <CurrentStepComponent
          key={currentStep}
          step={steps[currentStep]}
          hostData={hostData}
          updateHostData={updateHostData}
          onNext={nextStep}
          onPrev={prevStep}
          onComplete={completeOnboarding}
          isFirst={currentStep === 0}
          isLast={currentStep === steps.length - 1}
          loading={loading}
        />
      </AnimatePresence>
    </div>
  );
};

const WelcomeStep: React.FC<{
  step: OnboardingStep;
  onNext: () => void;
  isFirst: boolean;
}> = ({ step, onNext, isFirst }) => {
  const features = [
    {
      title: "AI-Powered Recommendations",
      description: "Our AI creates personalized recommendations for your guests based on their preferences and your local knowledge.",
      icon: "🤖",
      benefits: ["Personalized guest experiences", "Higher guest satisfaction", "Authentic local insights"]
    },
    {
      title: "Croatian Tourism Integration",
      description: "Access real-time data from Croatian tourism sources via Crawl4AI to keep your recommendations current.",
      icon: "🇭🇷",
      benefits: ["Live tourism updates", "Official event information", "Weather-based suggestions"]
    },
    {
      title: "Easy Guest Management",
      description: "Create temporary access codes for your guests and manage their experience from one dashboard.",
      icon: "👥",
      benefits: ["Simple guest onboarding", "Group preference tracking", "Activity feedback"]
    }
  ];

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.5 }}
    >
      <HeroSection
        title="Dobro došli u HostForGuest! 🇭🇷"
        subtitle="Welcome to the Future of Croatian Hospitality"
        description="Transform your hosting experience with AI-powered local guide services. Help your guests discover authentic Croatian experiences while building your reputation as a premium host."
        backgroundGradient="from-blue-600 via-teal-600 to-green-600"
        ctaText="Start Your Journey"
        ctaAction={onNext}
        secondaryCtaText="Learn More"
      />

      <FeatureSection
        title="Why Croatian Hosts Choose Us"
        subtitle="Join hundreds of hosts across Croatia who are creating exceptional guest experiences."
        features={features}
        className="bg-white"
      />
    </motion.div>
  );
};

const RegistrationStep: React.FC<{
  step: OnboardingStep;
  hostData: any;
  updateHostData: (data: any) => void;
  onNext: () => void;
  onPrev: () => void;
}> = ({ step, hostData, updateHostData, onNext, onPrev }) => {
  const { login: authLogin } = useAuth();
  const [formData, setFormData] = useState({
    email: hostData.email || '',
    password: '',
    confirmPassword: '',
    full_name: hostData.full_name || ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    if (!formData.email || !formData.full_name) {
      setError('Please fill in all required fields');
      return;
    }

    setLoading(true);

    try {
      // Split full name into first and last name
      const nameParts = formData.full_name.trim().split(' ');
      const firstName = nameParts[0] || '';
      const lastName = nameParts.slice(1).join(' ') || 'Host'; // Default to 'Host' if no last name

      // Register the host with required fields
      const response = await authApi.register({
        email: formData.email,
        password: formData.password,
        first_name: firstName,
        last_name: lastName,
        address: 'To be updated during onboarding', // Placeholder
        city: 'To be updated' // Placeholder
      });

      if (response.success && response.data) {
        const loginResult = await authLogin(formData.email, formData.password);

        if (loginResult.ok) {
          updateHostData({
            email: formData.email,
            full_name: formData.full_name,
            first_name: firstName,
            last_name: lastName,
            registered: true,
            host_id: response.data.id
          });
          onNext();
        } else {
          setError(
            loginResult.error ||
              "Registration successful but login failed. Please try logging in manually."
          );
        }
      } else {
        // Handle different error formats
        let errorMessage = 'Registration failed. Please try again.';
        if (response.error) {
          const err = response.error as unknown;
          if (typeof err === "string") {
            errorMessage = err;
          } else if (err && typeof err === "object" && !Array.isArray(err) && "detail" in err) {
            const d = (err as { detail: unknown }).detail;
            if (typeof d === "string") errorMessage = d;
          } else if (Array.isArray(err) && err.length > 0) {
            const first = err[0] as Record<string, unknown>;
            errorMessage = String(first.msg ?? first.message ?? errorMessage);
          }
        }
        setError(errorMessage);
      }
    } catch (error) {
      console.error('Registration error:', error);
      setError('Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="max-w-4xl mx-auto px-6 py-12"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8 }}
    >
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          {step.title}
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          {step.description}
        </p>
      </div>

      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>Create Your Host Account</CardTitle>
          <CardDescription>
            Join the Croatian Tourism Host Platform and start offering exceptional experiences to your guests.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-3 bg-red-50 border border-red-200 rounded-lg"
              >
                <p className="text-red-700 text-sm font-medium">
                  ❌ {typeof error === 'string' ? error : JSON.stringify(error)}
                </p>
              </motion.div>
            )}

            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 mb-2">
                Full Name *
              </label>
              <input
                type="text"
                id="full_name"
                name="full_name"
                value={formData.full_name}
                onChange={handleInputChange}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="Enter your full name"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email Address *
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="your.email@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password *
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                minLength={8}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="Create a secure password (min. 8 characters)"
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                Confirm Password *
              </label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                required
                minLength={8}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="Confirm your password"
              />
            </div>

            <div className="flex gap-4">
              <Button
                type="button"
                variant="outline"
                onClick={onPrev}
                className="flex-1"
              >
                ← Back
              </Button>
              <Button
                type="submit"
                className="flex-1 bg-gradient-to-r from-blue-600 to-teal-600 hover:from-blue-700 hover:to-teal-700"
                disabled={loading}
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    Creating Account...
                  </div>
                ) : (
                  'Create Account & Continue →'
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="text-center mt-8">
        <p className="text-sm text-gray-500">
          🔒 Your information is secure and will only be used to create your host profile
        </p>
      </div>
    </motion.div>
  );
};

const BasicInfoStep: React.FC<{
  step: OnboardingStep;
  hostData: any;
  updateHostData: (data: any) => void;
  onNext: () => void;
  onPrev: () => void;
}> = ({ step, hostData, updateHostData, onNext, onPrev }) => {
  const [formData, setFormData] = useState({
    business_name: hostData.business_name || '',
    location: hostData.location || '',
    property_type: hostData.property_type || 'apartment',
    city: hostData.city || '',
    region: hostData.region || 'Istria',
    languages: hostData.languages || ['Croatian', 'English'],
    specialties: hostData.specialties || [],
    local_experience: hostData.local_experience || '',
    preferred_guests: hostData.preferred_guests || [],
    location_story: hostData.location_story || '',
    google_place_id: hostData.google_place_id || '',
    coordinates: hostData.coordinates ?? null as { lat: number; lng: number } | null,
    verified_location: Boolean(hostData.verified_location),
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [attemptedSubmit, setAttemptedSubmit] = useState(false);
  const [geocodeStatus, setGeocodeStatus] = useState<
    "idle" | "loading" | "exact" | "approx" | "error"
  >("idle");
  const geocodeTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const propertyTypes = ['apartment', 'villa', 'house', 'room', 'studio'];
  const croatianRegions = ['Istria', 'Dalmatia', 'Kvarner', 'Central Croatia', 'Slavonia'];
  const availableLanguages = ['Croatian', 'English', 'German', 'Italian', 'French', 'Spanish'];
  const specialtyOptions = ['Local History', 'Gastronomy', 'Nature Activities', 'Cultural Events', 'Wine Tourism', 'Adventure Sports'];

  // Auto-save form data to localStorage
  React.useEffect(() => {
    const saveTimer = setTimeout(() => {
      localStorage.setItem('onboarding_basic_info', JSON.stringify(formData));
    }, 1000); // Save 1 second after user stops typing

    return () => clearTimeout(saveTimer);
  }, [formData]);

  // Restore saved data on mount
  React.useEffect(() => {
    const saved = localStorage.getItem('onboarding_basic_info');
    if (saved) {
      try {
        const savedData = JSON.parse(saved);
        setFormData(prev => ({ ...prev, ...savedData }));
      } catch (e) {
        console.error('Failed to restore saved data:', e);
      }
    }
  }, []);

  // Validate required fields
  const validateForm = (
    data: typeof formData = formData,
    geoStatus: typeof geocodeStatus = geocodeStatus
  ): boolean => {
    const errors: Record<string, string> = {};

    if (!data.business_name.trim()) {
      errors.business_name = 'Property name is required';
    }
    if (!data.city.trim()) {
      errors.city = 'City is required';
    }
    if (!data.local_experience) {
      errors.local_experience = 'Please select how long you\'ve lived here';
    }
    if (!data.preferred_guests || data.preferred_guests.length === 0) {
      errors.preferred_guests = 'Please select at least one guest type';
    }
    if (!data.location_story.trim()) {
      errors.location_story = 'Please tell us what makes your location special';
    } else if (data.location_story.trim().length < 20) {
      errors.location_story = 'Please write at least 20 characters';
    }

    if (data.city.trim() && !data.coordinates) {
      if (geoStatus === "error") {
        errors.location =
          "We could not locate this address — refine it or use Verify with Google Places.";
      } else if (geoStatus !== "loading") {
        errors.city = "Confirm your location so guests get accurate distances to events.";
      }
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Calculate completion status
  const getCompletionStatus = () => {
    const requiredFields = [
      formData.business_name.trim(),
      formData.city.trim(),
      formData.local_experience,
      formData.preferred_guests.length > 0,
      formData.location_story.trim().length >= 20
    ];
    const completed = requiredFields.filter(Boolean).length;
    const total = requiredFields.length;
    return { completed, total, percentage: Math.round((completed / total) * 100) };
  };

  const status = getCompletionStatus();

  const runAddressGeocode = React.useCallback(
    async (fields?: { location?: string; city?: string; region?: string }) => {
      const address = (fields?.location ?? formData.location ?? "").trim();
      const city = (fields?.city ?? formData.city ?? "").trim();
      if (!address && !city) {
        setGeocodeStatus("idle");
        return;
      }
      setGeocodeStatus("loading");
      const res = await hostsApi.geocodeLocation({
        address: address || city,
        city: city || undefined,
        county: fields?.region ?? formData.region,
      });
      if (res.success && res.data) {
        setFormData((prev) => ({
          ...prev,
          coordinates: { lat: res.data!.latitude, lng: res.data!.longitude },
          verified_location: res.data!.precision === "address",
        }));
        setGeocodeStatus(res.data.precision === "address" ? "exact" : "approx");
      } else {
        setGeocodeStatus("error");
      }
    },
    [formData.location, formData.city, formData.region]
  );

  React.useEffect(() => {
    if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current);
    const address = (formData.location || "").trim();
    const city = (formData.city || "").trim();
    if (!address && !city) {
      setGeocodeStatus("idle");
      return;
    }
    geocodeTimerRef.current = setTimeout(() => {
      void runAddressGeocode();
    }, 900);
    return () => {
      if (geocodeTimerRef.current) clearTimeout(geocodeTimerRef.current);
    };
  }, [formData.location, formData.city, formData.region, runAddressGeocode]);

  const verifyWithGooglePlaces = async (location: string) => {
    if (!location.trim()) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/onboarding/google-places/${encodeURIComponent(location)}`
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response:', text);
        throw new Error('Server returned non-JSON response');
      }

      const data = await response.json();

      if (data.success && data.place_info) {
        const place = data.place_info;
        setFormData({
          ...formData,
          location: place.address || formData.location,
          google_place_id: place.place_id,
          coordinates: place.location,
          verified_location: true
        });

        alert(`✅ Location verified: ${place.name}\n📍 ${place.address}`);
      } else {
        alert(`❌ Could not verify location: ${data.error || 'Please check the address.'}`);
      }
    } catch (error) {
      console.error('Google Places verification failed:', error);
      alert(`❌ Location verification failed: ${error instanceof Error ? error.message : 'Please try again.'}`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAttemptedSubmit(true);

    let submitData = formData;
    let submitGeoStatus = geocodeStatus;
    const address = (formData.location || "").trim();
    const city = (formData.city || "").trim();
    if ((address || city) && !formData.coordinates) {
      setGeocodeStatus("loading");
      submitGeoStatus = "loading";
      const res = await hostsApi.geocodeLocation({
        address: address || city,
        city: city || undefined,
        county: formData.region,
      });
      if (res.success && res.data) {
        submitGeoStatus = res.data.precision === "address" ? "exact" : "approx";
        submitData = {
          ...formData,
          coordinates: { lat: res.data.latitude, lng: res.data.longitude },
          verified_location: res.data.precision === "address",
        };
        setFormData(submitData);
        setGeocodeStatus(submitGeoStatus);
      } else {
        submitGeoStatus = "error";
        setGeocodeStatus("error");
      }
    }

    if (!validateForm(submitData, submitGeoStatus)) {
      // Scroll to first error
      const firstErrorField = Object.keys(validationErrors)[0];
      const element = document.querySelector(`[name="${firstErrorField}"]`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }

    // Clear localStorage on successful submit
    localStorage.removeItem('onboarding_basic_info');
    updateHostData(submitData);
    onNext();
  };

  const FieldStatus = ({ isValid, isRequired }: { isValid: boolean; isRequired: boolean }) => {
    if (!isRequired) return <span className="text-xs text-gray-400 ml-1">(optional)</span>;
    if (isValid) return <span className="text-green-600 ml-1">✓</span>;
    if (attemptedSubmit) return <span className="text-red-600 ml-1">⚠️</span>;
    return <span className="text-red-500 ml-1">*</span>;
  };

  return (
    <motion.div
      className="max-w-4xl mx-auto px-6 py-12"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.5 }}
    >
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">{step.title}</h1>
        <p className="text-xl text-gray-600">{step.description}</p>
      </div>

      {/* Progress Indicator */}
      <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-blue-900">Form Completion</h3>
          <span className="text-sm font-medium text-blue-700">{status.completed} of {status.total} required</span>
        </div>
        <div className="w-full bg-blue-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${status.percentage}%` }}
          />
        </div>
        {status.completed < status.total && (
          <p className="text-xs text-blue-700 mt-2">
            💡 Fill in all required fields (marked with *) to continue
          </p>
        )}
      </div>

      <Card className="bg-white shadow-xl">
        <CardContent className="p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Welcome section */}
            <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-semibold">
                    {hostData.full_name ? hostData.full_name.split(' ').map((n: string) => n[0]).join('').toUpperCase() : 'U'}
                  </span>
                </div>
                <div>
                  <p className="font-medium text-gray-900">Welcome, {hostData.full_name}!</p>
                  <p className="text-sm text-gray-600">{hostData.email}</p>
                </div>
              </div>
            </div>

            {/* Property Details Section */}
            <div className="space-y-6 border-b border-gray-200 pb-6">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                🏠 Property Details
              </h3>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Business/Property Name
                  <FieldStatus isValid={!!formData.business_name.trim()} isRequired={true} />
                </label>
                <input
                  type="text"
                  name="business_name"
                  value={formData.business_name}
                  onChange={(e) => setFormData({ ...formData, business_name: e.target.value })}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${validationErrors.business_name && attemptedSubmit ? 'border-red-500' : 'border-gray-300'
                    }`}
                  placeholder="e.g., Villa Adriatic, Apartment Lovran..."
                />
                {validationErrors.business_name && attemptedSubmit && (
                  <p className="text-red-600 text-sm mt-1">{validationErrors.business_name}</p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Property Type
                    <FieldStatus isValid={true} isRequired={false} />
                  </label>
                  <select
                    value={formData.property_type}
                    onChange={(e) => setFormData({ ...formData, property_type: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    {propertyTypes.map(type => (
                      <option key={type} value={type}>
                        {type.charAt(0).toUpperCase() + type.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    City
                    <FieldStatus isValid={!!formData.city.trim()} isRequired={true} />
                  </label>
                  <input
                    type="text"
                    name="city"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${validationErrors.city && attemptedSubmit ? 'border-red-500' : 'border-gray-300'
                      }`}
                    placeholder="e.g., Lovran, Opatija, Rovinj..."
                  />
                  {validationErrors.city && attemptedSubmit && (
                    <p className="text-red-600 text-sm mt-1">{validationErrors.city}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Region
                  <FieldStatus isValid={true} isRequired={false} />
                </label>
                <select
                  value={formData.region}
                  onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {croatianRegions.map(region => (
                    <option key={region} value={region}>{region}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Address
                  <FieldStatus isValid={true} isRequired={false} />
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    onBlur={() => { void runAddressGeocode(); }}
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g., Oprić 71, 51450 Lovran, Croatia"
                  />
                  <Button
                    type="button"
                    onClick={() => verifyWithGooglePlaces(formData.location)}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    📍 Google
                  </Button>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
                  {geocodeStatus === "loading" && (
                    <span className="text-gray-500">Locating address…</span>
                  )}
                  {geocodeStatus === "exact" && (
                    <span className="text-green-700">📍 Location verified</span>
                  )}
                  {geocodeStatus === "approx" && (
                    <span className="text-amber-700">📍 Location verified (approximate)</span>
                  )}
                  {geocodeStatus === "error" && (
                    <span className="text-amber-800">⚠️ Could not verify — add city or use Google verify</span>
                  )}
                  {formData.coordinates && geocodeStatus !== "loading" && (
                    <span className="text-xs text-gray-500">
                      {formData.coordinates.lat.toFixed(5)}, {formData.coordinates.lng.toFixed(5)}
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  Coordinates auto-fill when you finish typing. Optional: Google Places for place details.
                </p>
              </div>
            </div>

            {/* About You Section */}
            <div className="space-y-6 border-b border-gray-200 pb-6">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                👤 About You
              </h3>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  How long have you lived in this area?
                  <FieldStatus isValid={!!formData.local_experience} isRequired={true} />
                </label>
                <select
                  name="local_experience"
                  value={formData.local_experience || ''}
                  onChange={(e) => setFormData({ ...formData, local_experience: e.target.value })}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${validationErrors.local_experience && attemptedSubmit ? 'border-red-500' : 'border-gray-300'
                    }`}
                >
                  <option value="">Select...</option>
                  <option value="less_than_1_year">Less than 1 year</option>
                  <option value="1_to_5_years">1-5 years</option>
                  <option value="5_to_15_years">5-15 years</option>
                  <option value="15_plus_years">15+ years</option>
                  <option value="born_here">Born here</option>
                </select>
                {validationErrors.local_experience && attemptedSubmit && (
                  <p className="text-red-600 text-sm mt-1">{validationErrors.local_experience}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  What type of guests do you most enjoy hosting?
                  <FieldStatus isValid={formData.preferred_guests.length > 0} isRequired={true} />
                  {formData.preferred_guests.length > 0 && (
                    <span className="ml-2 text-xs text-blue-600">({formData.preferred_guests.length} selected)</span>
                  )}
                </label>
                <div className={`grid grid-cols-2 gap-3 p-4 rounded-lg ${validationErrors.preferred_guests && attemptedSubmit ? 'border-2 border-red-500 bg-red-50' : 'border border-gray-200'
                  }`}>
                  {[
                    'Young couples', 'Families with children', 'Solo travelers',
                    'Groups of friends', 'Business travelers', 'Senior travelers',
                    'Adventure seekers', 'Cultural enthusiasts'
                  ].map(guestType => (
                    <label key={guestType} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.preferred_guests?.includes(guestType) || false}
                        onChange={(e) => {
                          const currentGuests = formData.preferred_guests || [];
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              preferred_guests: [...currentGuests, guestType]
                            });
                          } else {
                            setFormData({
                              ...formData,
                              preferred_guests: currentGuests.filter((g: string) => g !== guestType)
                            });
                          }
                        }}
                        className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="text-sm text-gray-700">{guestType}</span>
                    </label>
                  ))}
                </div>
                {validationErrors.preferred_guests && attemptedSubmit && (
                  <p className="text-red-600 text-sm mt-1">{validationErrors.preferred_guests}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  What makes your location special? (Tell us in your own words)
                  <FieldStatus isValid={formData.location_story.trim().length >= 20} isRequired={true} />
                  <span className="ml-2 text-xs text-gray-500">
                    ({formData.location_story.length} characters{formData.location_story.length < 20 ? ', minimum 20' : ''})
                  </span>
                </label>
                <textarea
                  name="location_story"
                  value={formData.location_story || ''}
                  onChange={(e) => setFormData({ ...formData, location_story: e.target.value })}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${validationErrors.location_story && attemptedSubmit ? 'border-red-500' : 'border-gray-300'
                    }`}
                  rows={4}
                  placeholder="e.g., 'My family has lived here for generations. I know every hidden beach, the best time to visit the local market, and which konoba serves the freshest fish...'"
                />
                {validationErrors.location_story && attemptedSubmit && (
                  <p className="text-red-600 text-sm mt-1">{validationErrors.location_story}</p>
                )}
              </div>
            </div>

            {/* Optional Section */}
            <div className="space-y-6">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                ⭐ Your Specialties & Interests
                <span className="text-xs text-gray-500 font-normal">(optional - you can add these later)</span>
              </h3>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Languages You Speak
                  <FieldStatus isValid={true} isRequired={false} />
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {availableLanguages.map(language => (
                    <label key={language} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.languages.includes(language)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              languages: [...formData.languages, language]
                            });
                          } else {
                            setFormData({
                              ...formData,
                              languages: formData.languages.filter((l: string) => l !== language)
                            });
                          }
                        }}
                        className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="text-sm text-gray-700">{language}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Your Specialties & Interests
                  <FieldStatus isValid={true} isRequired={false} />
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {specialtyOptions.map(specialty => (
                    <label key={specialty} className="flex items-center">
                      <input
                        type="checkbox"
                        checked={formData.specialties.includes(specialty)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              specialties: [...formData.specialties, specialty]
                            });
                          } else {
                            setFormData({
                              ...formData,
                              specialties: formData.specialties.filter((s: string) => s !== specialty)
                            });
                          }
                        }}
                        className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                      />
                      <span className="text-sm text-gray-700">{specialty}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-between pt-6 border-t border-gray-200">
              <Button type="button" variant="outline" onClick={onPrev}>
                ← Previous
              </Button>
              <Button
                type="submit"
                gradient
                disabled={status.completed < status.total}
                className={status.completed < status.total ? 'opacity-50 cursor-not-allowed' : ''}
                title={status.completed < status.total ? `Complete ${status.total - status.completed} more required field${status.total - status.completed > 1 ? 's' : ''}` : ''}
              >
                Continue to AI Profile →
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Auto-save indicator */}
      <div className="text-center mt-4 text-xs text-gray-500">
        💾 Your progress is automatically saved
      </div>
    </motion.div>
  );
};

const AIProfileStep: React.FC<{
  step: OnboardingStep;
  hostData: any;
  updateHostData: (data: any) => void;
  onNext: () => void;
  onPrev: () => void;
}> = ({ step, hostData, updateHostData, onNext, onPrev }) => {
  const [aiSuggestions, setAiSuggestions] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedSuggestions, setSelectedSuggestions] = useState<any>({
    business_description: null,
    welcome_message: null,
    host_story: null
  });

  const generateSuggestions = async () => {
    setLoading(true);
    try {
      const response = await onboardingApi.generateProfileSuggestions(hostData);

      if (response.success) {
        // API client wraps backend response in data field
        const payload = response.data as { suggestions?: Record<string, unknown> } | undefined;
        const suggestions = payload?.suggestions;

        // Always use fallback layout for selection functionality
        // BentoGrid component doesn't support clickable suggestions
        setAiSuggestions({
          ...suggestions,
          ui_components: null
        });

        // Pre-select the first option in each category for better UX
        const initialSelections: any = {};
        if (suggestions?.business_description && Array.isArray(suggestions.business_description) && suggestions.business_description.length > 0) {
          initialSelections.business_description = suggestions.business_description[0];
        }
        if (suggestions?.welcome_message && Array.isArray(suggestions.welcome_message) && suggestions.welcome_message.length > 0) {
          initialSelections.welcome_message = suggestions.welcome_message[0];
        }
        if (suggestions?.host_story && Array.isArray(suggestions.host_story) && suggestions.host_story.length > 0) {
          initialSelections.host_story = suggestions.host_story[0];
        }
        setSelectedSuggestions(initialSelections);
      } else {
        console.error('API returned error:', response.error);
        alert(`Failed to generate suggestions: ${response.error}`);
      }
    } catch (error) {
      console.error('Error generating suggestions:', error);
      alert(`Error generating suggestions: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionSelect = (category: string, suggestion: string) => {
    setSelectedSuggestions({
      ...selectedSuggestions,
      [category]: suggestion
    });
  };

  React.useEffect(() => {
    if (hostData.business_name && hostData.city) {
      generateSuggestions();
    }
  }, [hostData.business_name, hostData.city]);

  const handleNext = () => {
    updateHostData({
      ...selectedSuggestions,
      ai_generated: true
    });
    onNext();
  };

  return (
    <motion.div
      className="max-w-6xl mx-auto px-6 py-12"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.5 }}
    >
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">{step.title}</h1>
        <p className="text-xl text-gray-600">{step.description}</p>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">AI is creating your authentic Croatian host profile...</p>
        </div>
      ) : aiSuggestions ? (
        <div className="space-y-8">

          {aiSuggestions.ui_components?.bento_grid ? (
            <BentoGrid
              items={aiSuggestions.ui_components.bento_grid.props.items}
              className="grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
            />
          ) : (
            /* Fallback 3-column layout for direct AI suggestions */
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Business Description Column */}
              {aiSuggestions.business_description && (
                <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="text-2xl">🏠</div>
                    <h3 className="text-lg font-semibold text-gray-900">Business Description</h3>
                  </div>
                  <p className="text-sm text-gray-500 mb-4">AI-generated authentic descriptions</p>
                  <div className="space-y-3">
                    {aiSuggestions.business_description.map((desc: string, idx: number) => {
                      const isSelected = selectedSuggestions.business_description === desc;
                      return (
                        <div
                          key={idx}
                          onClick={() => handleSuggestionSelect('business_description', desc)}
                          className={`p-3 rounded-lg text-sm transition-all cursor-pointer border-2 ${isSelected
                            ? 'bg-blue-100 border-blue-500 text-blue-900 shadow-md'
                            : 'bg-gray-50 border-transparent text-gray-700 hover:bg-blue-50 hover:border-blue-200'
                            }`}
                        >
                          <div className="flex items-start gap-2">
                            {isSelected && <span className="text-blue-600 font-bold text-lg">✓</span>}
                            <span className={isSelected ? 'font-medium' : ''}>{desc}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Welcome Messages Column */}
              {aiSuggestions.welcome_message && (
                <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="text-2xl">👋</div>
                    <h3 className="text-lg font-semibold text-gray-900">Welcome Messages</h3>
                  </div>
                  <p className="text-sm text-gray-500 mb-4">Warm Croatian hospitality greetings</p>
                  <div className="space-y-3">
                    {aiSuggestions.welcome_message.map((msg: string, idx: number) => {
                      const isSelected = selectedSuggestions.welcome_message === msg;
                      return (
                        <div
                          key={idx}
                          onClick={() => handleSuggestionSelect('welcome_message', msg)}
                          className={`p-3 rounded-lg text-sm transition-all cursor-pointer border-2 ${isSelected
                            ? 'bg-blue-100 border-blue-500 text-blue-900 shadow-md'
                            : 'bg-gray-50 border-transparent text-gray-700 hover:bg-blue-50 hover:border-blue-200'
                            }`}
                        >
                          <div className="flex items-start gap-2">
                            {isSelected && <span className="text-blue-600 font-bold text-lg">✓</span>}
                            <span className={isSelected ? 'font-medium' : ''}>{msg}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Host Story Column */}
              {aiSuggestions.host_story && (
                <div className="bg-white rounded-xl p-6 shadow-lg border border-gray-100">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="text-2xl">📖</div>
                    <h3 className="text-lg font-semibold text-gray-900">Host Story</h3>
                  </div>
                  <p className="text-sm text-gray-500 mb-4">Personal stories and local connection</p>
                  <div className="space-y-3">
                    {aiSuggestions.host_story.map((story: string, idx: number) => {
                      const isSelected = selectedSuggestions.host_story === story;
                      return (
                        <div
                          key={idx}
                          onClick={() => handleSuggestionSelect('host_story', story)}
                          className={`p-3 rounded-lg text-sm transition-all cursor-pointer border-2 ${isSelected
                            ? 'bg-blue-100 border-blue-500 text-blue-900 shadow-md'
                            : 'bg-gray-50 border-transparent text-gray-700 hover:bg-blue-50 hover:border-blue-200'
                            }`}
                        >
                          <div className="flex items-start gap-2">
                            {isSelected && <span className="text-blue-600 font-bold text-lg">✓</span>}
                            <span className={isSelected ? 'font-medium' : ''}>{story}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Selection Summary */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <h4 className="font-semibold text-green-900 mb-2 flex items-center gap-2">
              <span className="text-green-600">✓</span>
              Your Selections Summary
            </h4>
            <div className="text-sm text-green-800 space-y-1">
              <p><strong>Business Description:</strong> {selectedSuggestions.business_description ? '✓ Selected' : '⚠️ Please select one'}</p>
              <p><strong>Welcome Message:</strong> {selectedSuggestions.welcome_message ? '✓ Selected' : '⚠️ Please select one'}</p>
              <p><strong>Host Story:</strong> {selectedSuggestions.host_story ? '✓ Selected' : '⚠️ Please select one'}</p>
            </div>
            {(!selectedSuggestions.business_description || !selectedSuggestions.welcome_message || !selectedSuggestions.host_story) && (
              <p className="text-xs text-green-700 mt-2 italic">Click on any option above to select it for your profile.</p>
            )}
          </div>

          <div className="flex justify-between">
            <Button variant="outline" onClick={onPrev}>
              Previous
            </Button>
            <div className="flex gap-3">
              <Button variant="outline" onClick={generateSuggestions}>
                Regenerate Suggestions
              </Button>
              <Button
                gradient
                onClick={handleNext}
                disabled={!selectedSuggestions.business_description || !selectedSuggestions.welcome_message || !selectedSuggestions.host_story}
              >
                Continue with Selections
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">🤖</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Ready to Generate Your Profile?
          </h3>
          <p className="text-gray-600 mb-6">
            Our AI will create authentic suggestions based on your location and specialties.
          </p>
          <Button gradient onClick={generateSuggestions}>
            Generate AI Suggestions
          </Button>
        </div>
      )}
    </motion.div>
  );
};

const AttractionsStep: React.FC<{
  step: OnboardingStep;
  hostData: any;
  updateHostData: (data: any) => void;
  onNext: () => void;
  onPrev: () => void;
}> = ({ step, hostData, updateHostData, onNext, onPrev }) => {
  const [attractions, setAttractions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingAttraction, setEditingAttraction] = useState<any | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);

  const generateAttractions = async () => {
    console.log('🎯 Starting attraction generation for:', hostData.city);
    setLoading(true);
    setError(null);
    try {
      // Enhanced request with more personalized data
      const response = await onboardingApi.generateAttractionSuggestions(
        {
          city: hostData.city,
          region: hostData.region,
          address: hostData.location,
          coordinates: hostData.coordinates
        },
        hostData.specialties || [],
        {
          local_experience: hostData.local_experience,
          preferred_guests: hostData.preferred_guests,
          location_story: hostData.location_story,
          knowledge_level: hostData.local_experience === 'born_here' ? 'expert' :
            hostData.local_experience === '15_plus_years' ? 'expert' :
              hostData.local_experience === '5_to_15_years' ? 'intermediate' : 'beginner'
        }
      );
      if (response.success) {
        // Handle both API client wrapped format and direct backend format
        const responseData = (response.data ?? response) as Record<string, unknown>;
        const attractions = Array.isArray(responseData.attractions)
          ? responseData.attractions
          : [];

        console.log('✅ Full API response keys:', Object.keys(responseData));
        console.log('✅ Attractions received:', attractions.length, 'attractions');
        console.log('First attraction data structure:', JSON.stringify(attractions[0], null, 2));

        // IMPORTANT: Only use the attractions array, ignore ui_components
        if (attractions && Array.isArray(attractions)) {
          // Add unique IDs to each attraction
          const attractionsWithIds = attractions.map((attr: any, idx: number) => ({
            ...attr,
            id: `attraction-${Date.now()}-${idx}`
          }));
          setAttractions(attractionsWithIds);
        } else {
          console.error('❌ Attractions is not an array:', attractions);
          setError('Invalid attractions data received');
        }

        // Optionally enhance with Google Places data (don't let this block the UI)
        if (hostData.coordinates) {
          try {
            await enhanceWithGooglePlaces();
          } catch (error) {
            console.warn('Google Places enhancement failed, continuing without it:', error);
          }
        }
      } else {
        console.error('❌ Attractions API returned error:', response.error);
        setError(`Failed to generate attractions: ${response.error}`);
      }
    } catch (error) {
      console.error('❌ Error generating attractions:', error);
      setError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      console.log('🔄 Setting loading to false');
      setLoading(false);
    }
  };

  const enhanceWithGooglePlaces = async () => {
    try {
      // Get nearby attractions from Google Places with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      const response = await fetch(
        `${API_BASE_URL}/api/v1/onboarding/google-places/nearby?lat=${hostData.coordinates.lat}&lng=${hostData.coordinates.lng}`,
        { signal: controller.signal }
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        console.error('Non-JSON response:', text);
        return;
      }

      const data = await response.json();

      if (data.success && data.nearby_places) {
        // Add Google Places suggestions to our AI-generated attractions
        const googleAttractions = data.nearby_places.map((place: any, idx: number) => ({
          id: `google-${Date.now()}-${idx}`,
          name: place.name,
          description: `${place.name} - ${place.types.join(', ')}. Rating: ${place.rating}/5`,
          category: mapGoogleTypeToCategory(place.types[0]),
          authenticity_level: 'high',
          cost_estimate: 'moderate',
          best_time: 'anytime',
          difficulty: 'easy',
          google_place: true,
          google_data: place
        }));

        setAttractions(prev => [...prev, ...googleAttractions.slice(0, 3)]); // Add top 3 Google suggestions
      }
    } catch (error) {
      console.error('Error enhancing with Google Places:', error);
    }
  };

  const mapGoogleTypeToCategory = (googleType: string): string => {
    const mapping: { [key: string]: string } = {
      'restaurant': 'culinary',
      'tourist_attraction': 'cultural',
      'park': 'nature',
      'museum': 'cultural',
      'beach': 'beach',
      'church': 'cultural',
      'natural_feature': 'nature'
    };
    return mapping[googleType] || 'experience';
  };

  React.useEffect(() => {
    if (hostData.city) {
      generateAttractions();
    }
  }, []);

  const handleNext = () => {
    updateHostData({ local_attractions: attractions });
    onNext();
  };

  const handleEditAttraction = (attraction: any, index: number) => {
    setEditingAttraction({ ...attraction, index });
    setShowEditModal(true);
  };

  const handleDeleteAttraction = (index: number) => {
    if (confirm('Are you sure you want to delete this attraction?')) {
      setAttractions(prev => prev.filter((_, i) => i !== index));
    }
  };

  const handleAddCustomAttraction = () => {
    setEditingAttraction({
      id: `custom-${Date.now()}`,
      name: '',
      description: '',
      category: 'cultural',
      authenticity_level: 'high',
      cost_estimate: 'free',
      best_time: 'anytime',
      difficulty: 'easy',
      index: -1 // -1 indicates new attraction
    });
    setShowEditModal(true);
  };

  const handleSaveAttraction = (updatedAttraction: any) => {
    if (updatedAttraction.index === -1) {
      // New attraction
      const { index, ...attractionData } = updatedAttraction;
      setAttractions(prev => [...prev, attractionData]);
    } else {
      // Update existing attraction
      setAttractions(prev => prev.map((attr, idx) =>
        idx === updatedAttraction.index ? updatedAttraction : attr
      ));
    }
    setShowEditModal(false);
    setEditingAttraction(null);
  };

  return (
    <motion.div
      className="max-w-6xl mx-auto px-6 py-12"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.5 }}
    >
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">{step.title}</h1>
        <p className="text-xl text-gray-600">{step.description}</p>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="w-16 h-16 border-4 border-green-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Discovering hidden gems in {hostData.city}...</p>
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">⚠️</div>
          <h3 className="text-xl font-semibold text-red-600 mb-2">
            Oops! Something went wrong
          </h3>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="flex justify-center gap-3">
            <Button variant="outline" onClick={generateAttractions}>
              Try Again
            </Button>
            <Button variant="outline" onClick={onNext}>
              Skip for Now
            </Button>
          </div>
        </div>
      ) : attractions.length > 0 ? (
        <div className="space-y-8">
          {/* Info banner */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <div className="text-2xl">💡</div>
              <div>
                <h4 className="font-semibold text-blue-900 mb-1">Customize Your Local Knowledge</h4>
                <p className="text-sm text-blue-700">
                  These are AI-generated suggestions. Feel free to edit them, delete any you don&apos;t like, or add your own hidden gems!
                </p>
              </div>
            </div>
          </div>

          {/* Attractions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {attractions.map((attraction, index) => (
              <div key={attraction.id || index} className="bg-white rounded-xl p-6 shadow-lg border border-gray-200 hover:shadow-xl transition-shadow relative group">
                {/* Action buttons */}
                <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleEditAttraction(attraction, index)}
                    className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                    title="Edit attraction"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => handleDeleteAttraction(index)}
                    className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                    title="Delete attraction"
                  >
                    🗑️
                  </button>
                </div>

                <h3 className="font-semibold text-lg text-gray-900 mb-2 pr-20">
                  {attraction.name || `Attraction ${index + 1}`}
                </h3>
                <p className="text-gray-600 mb-4 text-sm line-clamp-3">
                  {attraction.description || 'No description available'}
                </p>
                <div className="flex items-center justify-between text-sm text-gray-500">
                  <span className="capitalize">{attraction.category || 'general'}</span>
                  <span className="bg-green-100 text-green-700 px-2 py-1 rounded-full text-xs">
                    {attraction.authenticity_level || 'medium'} authenticity
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm text-gray-500 mt-2">
                  <span>💰 {attraction.cost_estimate || 'unknown'}</span>
                  <span>🕒 {attraction.best_time || 'anytime'}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Add Custom Attraction Button */}
          <div className="flex justify-center">
            <Button
              variant="outline"
              onClick={handleAddCustomAttraction}
              className="border-dashed border-2 border-blue-400 text-blue-600 hover:bg-blue-50"
            >
              ➕ Add Your Own Hidden Gem
            </Button>
          </div>

          {/* Navigation buttons */}
          <div className="flex justify-between">
            <Button variant="outline" onClick={onPrev}>
              Previous
            </Button>
            <div className="flex gap-3">
              <Button variant="outline" onClick={generateAttractions}>
                Generate More
              </Button>
              <Button gradient onClick={handleNext}>
                Continue to Review ({attractions.length} attractions)
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">🏛️</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Ready to Discover Local Attractions?
          </h3>
          <p className="text-gray-600 mb-6">
            Let AI suggest authentic local experiences based on your area and expertise.
          </p>
          <Button gradient onClick={generateAttractions}>
            Discover Attractions
          </Button>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && editingAttraction && (
        <AttractionEditModal
          attraction={editingAttraction}
          onSave={handleSaveAttraction}
          onClose={() => {
            setShowEditModal(false);
            setEditingAttraction(null);
          }}
        />
      )}
    </motion.div>
  );
};

// Attraction Edit Modal Component
const AttractionEditModal: React.FC<{
  attraction: any;
  onSave: (attraction: any) => void;
  onClose: () => void;
}> = ({ attraction, onSave, onClose }) => {
  const [formData, setFormData] = useState(attraction);

  const categories = ['cultural', 'culinary', 'nature', 'beach', 'adventure', 'nightlife', 'experience'];
  const authenticityLevels = ['low', 'medium', 'high', 'authentic'];
  const costEstimates = ['free', 'budget', 'moderate', 'expensive', 'luxury'];
  const difficulties = ['easy', 'moderate', 'challenging'];
  const bestTimes = ['anytime', 'morning', 'afternoon', 'evening', 'night', 'weekend', 'summer', 'winter'];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      alert('Please enter an attraction name');
      return;
    }
    if (!formData.description.trim()) {
      alert('Please enter a description');
      return;
    }
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            {formData.index === -1 ? 'Add Custom Attraction' : 'Edit Attraction'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Attraction Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="e.g., Hidden Beach at Preluk, Old Town Konoba..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description *
            </label>
            <textarea
              required
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={4}
              placeholder="Share your local knowledge about this place..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Authenticity Level
              </label>
              <select
                value={formData.authenticity_level}
                onChange={(e) => setFormData({ ...formData, authenticity_level: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {authenticityLevels.map(level => (
                  <option key={level} value={level}>{level.charAt(0).toUpperCase() + level.slice(1)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cost Estimate
              </label>
              <select
                value={formData.cost_estimate}
                onChange={(e) => setFormData({ ...formData, cost_estimate: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {costEstimates.map(cost => (
                  <option key={cost} value={cost}>{cost.charAt(0).toUpperCase() + cost.slice(1)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Best Time to Visit
              </label>
              <select
                value={formData.best_time}
                onChange={(e) => setFormData({ ...formData, best_time: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {bestTimes.map(time => (
                  <option key={time} value={time}>{time.charAt(0).toUpperCase() + time.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex gap-4 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              gradient
              className="flex-1"
            >
              {formData.index === -1 ? 'Add Attraction' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

const ReviewStep: React.FC<{
  step: OnboardingStep;
  hostData: any;
  onPrev: () => void;
  onComplete: () => void;
  loading: boolean;
}> = ({ step, hostData, onPrev, onComplete, loading }) => {
  return (
    <motion.div
      className="max-w-4xl mx-auto px-6 py-12"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.5 }}
    >
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">{step.title}</h1>
        <p className="text-xl text-gray-600">{step.description}</p>
      </div>

      <Card className="bg-white shadow-xl">
        <CardHeader className="bg-gradient-to-r from-green-50 to-blue-50">
          <CardTitle>Your Croatian Host Profile</CardTitle>
          <CardDescription>
            Review your profile before going live
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          <div className="space-y-6">
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">Host & Business Information</h3>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p><strong>Host Name:</strong> {hostData.full_name}</p>
                <p><strong>Property Name:</strong> {hostData.business_name}</p>
                <p><strong>Property Type:</strong> {hostData.property_type}</p>
                <p><strong>Location:</strong> {hostData.city}, {hostData.region}</p>
                <p><strong>Local Experience:</strong> {hostData.local_experience?.replace('_', ' ')}</p>
                <p><strong>Languages:</strong> {hostData.languages?.join(', ')}</p>
                <p><strong>Specialties:</strong> {hostData.specialties?.join(', ')}</p>
                <p><strong>Preferred Guests:</strong> {hostData.preferred_guests?.join(', ')}</p>
              </div>
            </div>

            {hostData.local_attractions && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Local Attractions ({hostData.local_attractions.length})
                </h3>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {hostData.local_attractions.slice(0, 4).map((attraction: any, idx: number) => (
                      <div key={idx} className="text-sm">
                        • {attraction.name}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </CardContent>
        <CardFooter className="bg-gray-50">
          <div className="flex justify-between w-full">
            <Button variant="outline" onClick={onPrev} disabled={loading}>
              Previous
            </Button>
            <Button
              gradient
              onClick={onComplete}
              loading={loading}
              className="px-8"
            >
              Launch My Host Profile! 🚀
            </Button>
          </div>
        </CardFooter>
      </Card>
    </motion.div>
  );
};
