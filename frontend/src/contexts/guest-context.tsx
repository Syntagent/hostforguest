"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { GuestGroup, GuestPreference } from "@/lib/api";

interface GuestContextType {
  accessCode: string | null;
  guestGroup: GuestGroup | null;
  preferences: GuestPreference[];
  loading: boolean;
  error: string | null;
  setAccessCode: (code: string) => void;
  setGuestGroup: (group: GuestGroup | null) => void;
  setPreferences: (prefs: GuestPreference[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearGuestData: () => void;
}

const GuestContext = createContext<GuestContextType | undefined>(undefined);

export const useGuest = () => {
  const context = useContext(GuestContext);
  if (context === undefined) {
    throw new Error("useGuest must be used within a GuestProvider");
  }
  return context;
};

interface GuestProviderProps {
  children: ReactNode;
}

export const GuestProvider: React.FC<GuestProviderProps> = ({ children }) => {
  const [accessCode, setAccessCodeState] = useState<string | null>(null);
  const [guestGroup, setGuestGroupState] = useState<GuestGroup | null>(null);
  const [preferences, setPreferencesState] = useState<GuestPreference[]>([]);
  const [loading, setLoadingState] = useState(false);
  const [error, setErrorState] = useState<string | null>(null);

  const setAccessCode = (code: string) => {
    setAccessCodeState(code);
    // Store in localStorage for persistence
    if (typeof window !== "undefined") {
      localStorage.setItem("guest_access_code", code);
    }
  };

  const setGuestGroup = (group: GuestGroup | null) => {
    setGuestGroupState(group);
  };

  const setPreferences = (prefs: GuestPreference[]) => {
    setPreferencesState(prefs);
  };

  const setLoading = (loading: boolean) => {
    setLoadingState(loading);
  };

  const setError = (error: string | null) => {
    setErrorState(error);
  };

  const clearGuestData = () => {
    setAccessCodeState(null);
    setGuestGroupState(null);
    setPreferencesState([]);
    setLoadingState(false);
    setErrorState(null);
    
    // Clear from localStorage
    if (typeof window !== "undefined") {
      localStorage.removeItem("guest_access_code");
    }
  };

  // Load access code from localStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedCode = localStorage.getItem("guest_access_code");
      if (storedCode) {
        setAccessCodeState(storedCode);
      }
    }
  }, []);

  const value: GuestContextType = {
    accessCode,
    guestGroup,
    preferences,
    loading,
    error,
    setAccessCode,
    setGuestGroup,
    setPreferences,
    setLoading,
    setError,
    clearGuestData,
  };

  return (
    <GuestContext.Provider value={value}>
      {children}
    </GuestContext.Provider>
  );
};
