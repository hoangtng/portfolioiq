"use client";

// Auth context — provides current user state and login/logout helpers
// to every component. Wraps the entire app in src/app/layout.tsx.
//
// On mount it tries to load /api/auth/me/ using any stored access token.
// If that succeeds the user is logged in; if it fails (401, no token),
// user stays null and the user gets routed to /login by route guards.

import {
  createContext, useCallback, useContext, useEffect, useState, type ReactNode,
} from "react";
import { auth, tokens } from "@/lib/api";
import type { User, TokenPair } from "@/types";

interface AuthContextValue {
  user:        User | null;
  loading:     boolean;
  login:       (email: string, password: string) => Promise<void>;
  loginGoogle: (idToken: string) => Promise<void>;
  logout:      () => Promise<void>;
  refreshMe:   () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]       = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    if (!tokens.access) {
      setUser(null);
      return;
    }
    try {
      const me = await auth.me();
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  // Boot: try to load current user
  useEffect(() => {
    (async () => {
      await refreshMe();
      setLoading(false);
    })();
  }, [refreshMe]);

  const login = useCallback(async (email: string, password: string) => {
    const pair: TokenPair = await auth.login(email, password);
    tokens.set(pair);
    await refreshMe();
  }, [refreshMe]);

  const loginGoogle = useCallback(async (idToken: string) => {
    const resp = await auth.google(idToken);
    tokens.set({ access: resp.access, refresh: resp.refresh });
    await refreshMe();
  }, [refreshMe]);

  const logout = useCallback(async () => {
    await auth.logout();
    setUser(null);
    if (typeof window !== "undefined") window.location.href = "/login";
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, loginGoogle, logout, refreshMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
