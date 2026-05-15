"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { authApi, apiClient, Host, normalizeHostFromApi } from '@/lib/api';

interface AuthContextType {
  user: Host | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  logoutAllDevices: () => Promise<boolean>;
  isAuthenticated: boolean;
  clearError: () => void;
  // Development helper
  devLogin: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function logDev(...args: unknown[]) {
  if (process.env.NODE_ENV !== "development") return;
  if (process.env.NEXT_PUBLIC_DEBUG_AUTH !== "true") return;
  console.log(...args);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Host | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const isAuthenticated = !!user;

  // Check for existing session on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      // Clear any previous errors
      setError(null);

      // Check if we have session tokens in localStorage
      const sessionToken = typeof window !== 'undefined' ? localStorage.getItem('session_token') : null;

      logDev("🔍 checkAuthStatus - Session token:", sessionToken ? "present" : "null");

      if (!sessionToken) {
        logDev("⚠️ No session token found - user not logged in");
        setLoading(false);
        return;
      }

      logDev("✅ Session token found, verifying with backend...");

      // Verify session by getting current user
      const response = await authApi.getCurrentHost();

      logDev("📡 getCurrentHost response:", response);

      if (response.success && response.data) {
        logDev("✅ getCurrentHost successful, setting user data");
        const normalized = normalizeHostFromApi(response.data);
        if (normalized) setUser(normalized);
        else {
          apiClient.setSessionTokens(null, null);
          setError('Your session has expired. Please log in again.');
        }
      } else {
        logDev("❌ getCurrentHost failed, clearing tokens");
        // Session is invalid, clear tokens
        apiClient.setSessionTokens(null, null);
        setError('Your session has expired. Please log in again.');
      }
    } catch (error) {
      console.error('💥 Auth check failed:', error);
      apiClient.setSessionTokens(null, null);
      // Don't set error - just fail silently
    } finally {
      logDev("🏁 Setting loading to false");
      setLoading(false);
    }
  };

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      // Clear any previous errors
      setError(null);

      logDev("🔐 Login attempt for:", email);

      const response = await authApi.login(email, password);

      logDev("📡 Login response:", response);

      const payload = response.data as
        | {
            session_token?: string;
            refresh_token?: string;
            host?: Host;
          }
        | undefined;

      if (
        response.success &&
        payload &&
        typeof payload.session_token === "string" &&
        payload.host
      ) {
        logDev("✅ Login successful, storing tokens...");

        apiClient.setSessionTokens(
          payload.session_token,
          payload.refresh_token ?? null
        );

        logDev("💾 Tokens stored, setting user data...");

        const normalized = normalizeHostFromApi(payload.host);
        if (!normalized) {
          setError("Neispravan odgovor poslužitelja (host). Pokušaj ponovno.");
          return false;
        }
        setUser(normalized);
        return true;
      }

      logDev("❌ Login failed");
      setError(
        response.error ||
          "Neispravan email ili lozinka. Pokušaj ponovno."
      );
      return false;
    } catch (error) {
      console.error('💥 Login failed:', error);
      setError('Network error occurred. Please check your connection and try again.');
      return false;
    }
  };

  // Development helper for automatic login
  const devLogin = async (): Promise<boolean> => {
    if (process.env.NODE_ENV !== "development") {
      setError("Development login is disabled in this build.");
      return false;
    }

    try {
      logDev("🔧 Development: Attempting automatic login...");

      // Must match backend dev_login_seed_* (see app/core/config.py).
      const testEmail =
        process.env.NEXT_PUBLIC_DEV_LOGIN_EMAIL ||
        'dev@touristguide.local';
      const testPassword =
        process.env.NEXT_PUBLIC_DEV_LOGIN_PASSWORD ||
        'devlogin123';

      logDev(`🔧 Development: Using test credentials for ${testEmail}`);

      const success = await login(testEmail, testPassword);

      if (success) {
        logDev("✅ Development: Automatic login successful");
        // After successful login, verify the session
        await checkAuthStatus();
        return true;
      } else {
        logDev("❌ Development: Automatic login failed");
        return false;
      }
    } catch (error) {
      console.error('💥 Development: Automatic login error:', error);
      return false;
    }
  };

  const logout = async () => {
    try {
      // Call logout endpoint to invalidate session
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear tokens and user data
      apiClient.setSessionTokens(null, null);
      setUser(null);
      setError(null);
      router.push('/login');
    }
  };

  const logoutAllDevices = async (): Promise<boolean> => {
    try {
      const response = await authApi.logoutAllDevices();
      if (response.success) {
        // Clear tokens and user data
        apiClient.setSessionTokens(null, null);
        setUser(null);
        setError(null);
        router.push('/login');
        return true;
      }
      return false;
    } catch (error) {
      console.error('Logout all devices failed:', error);
      return false;
    }
  };

  const clearError = () => {
    setError(null);
  };

  const value: AuthContextType = {
    user,
    loading,
    error,
    login,
    logout,
    logoutAllDevices,
    isAuthenticated,
    clearError,
    devLogin,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Higher-order component for protecting routes
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  redirectTo: string = '/login'
) {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading && !isAuthenticated) {
        router.replace(redirectTo);
      }
    }, [isAuthenticated, loading, router, redirectTo]);

    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Checking authentication...</p>
          </div>
        </div>
      );
    }

    if (!isAuthenticated) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4 text-center">
          <p className="text-lg font-medium text-foreground">Sign-in required</p>
          <p className="max-w-md text-sm text-muted-foreground">
            The host dashboard is only available after you log in. If you are not redirected automatically,
            open the login page.
          </p>
          <a
            href={redirectTo}
            className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm hover:opacity-90"
          >
            Go to login
          </a>
        </div>
      );
    }

    return <Component {...props} />;
  };
}
