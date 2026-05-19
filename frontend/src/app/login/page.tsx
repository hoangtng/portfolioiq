"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, LogIn } from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import  imageLogo  from "@/static/images/icon.svg"
import Image from "next/image";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (cfg: { client_id: string; callback: (resp: { credential: string }) => void }) => void;
          renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
        };
      };
    };
  }
}

export default function LoginPage() {
  const router = useRouter();
  const { user, loading, login, loginGoogle } = useAuth();

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState("");
  const [submitting, setSubmitting] = useState(false);

  // If already logged in, redirect to dashboard
  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  // Google Sign-In
  useEffect(() => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID;
    if (!clientId) return;

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => {
      window.google?.accounts.id.initialize({
        client_id: clientId,
        callback: async (resp) => {
          try {
            await loginGoogle(resp.credential);
            router.replace("/dashboard");
          } catch (e) {
            setError(e instanceof ApiError ? e.message : "Google login failed");
          }
        },
      });
      const btn = document.getElementById("google-btn");
      if (btn) {
        window.google?.accounts.id.renderButton(btn, {
          theme: "filled_black", size: "large", width: 320,
        });
      }
    };
    document.body.appendChild(script);
    return () => { document.body.removeChild(script); };
  }, [router, loginGoogle]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? typeof err.data === "object" && err.data
            ? JSON.stringify(err.data).replace(/[{}"\[\]]/g, "").replace(/,/g, " · ")
            : err.message
          : "Login failed",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12 relative">
      {/* Subtle background grid */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,255,170,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,170,0.5) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }} />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-10">
          <div className="w-14 h-14 rounded-xl bg-accent-gradient flex items-center justify-center font-bold text-bg-deepest text-xl shadow-glow mb-4">
            <Image src={imageLogo} alt="PortfolioIQ" width={36} height={36} className="rounded-lg" />
          </div>
          <div className="font-mono font-bold text-lg tracking-[0.2em] text-ink">PORTFOLIOIQ</div>
          <div className="font-mono text-[11px] text-accent/60 mt-1">AI powered Portfolio</div>
        </div>

        {/* Card */}
        <div className="card p-6 sm:p-8">
          <h1 className="font-mono text-lg font-semibold mb-1">
            <span className="text-accent">{">"}</span> Login
          </h1>
          <p className="font-mono text-xs text-ink-muted mb-6">Login to continue</p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="label">email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="ethan@example.com"
                className="input"
              />
            </div>

            <div>
              <label className="label">password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
                className="input"
              />
            </div>

            {error && (
              <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg">
                ! {error}
              </div>
            )}

            <button type="submit" disabled={submitting} className="btn-primary mt-2">
              {submitting ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> signing in</>
              ) : (
                <><LogIn className="w-4 h-4" /> sign in</>
              )}
            </button>
          </form>

          {process.env.NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID && (
            <>
              <div className="flex items-center gap-3 my-6">
                <div className="flex-1 h-px bg-line" />
                <span className="font-mono text-[10px] uppercase tracking-wider text-ink-faint">or</span>
                <div className="flex-1 h-px bg-line" />
              </div>
              <div id="google-btn" className="flex justify-center" />
            </>
          )}

          <div className="text-center mt-6 font-mono text-xs text-ink-muted">
            Don&apos;t have an account ?{" "}
            <Link href="/register" className="text-accent hover:underline">Register</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
