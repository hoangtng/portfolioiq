"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, UserPlus } from "lucide-react";

import { auth, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import  imageLogo  from "@/static/images/icon.svg"
import Image from "next/image";

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email,     setEmail]     = useState("");
  const [firstName, setFirstName] = useState("");
  const [password,  setPassword]  = useState("");
  const [error,     setError]     = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await auth.register({ email, password, first_name: firstName });
      // Auto-login right after registration
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? typeof err.data === "object" && err.data
            ? JSON.stringify(err.data).replace(/[{}"\[\]]/g, "").replace(/,/g, " · ")
            : err.message
          : "Registration failed",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-10">
          <div className="w-14 h-14 rounded-xl bg-accent-gradient flex items-center justify-center font-bold text-bg-deepest text-xl shadow-glow mb-4">
            <Image src={imageLogo} alt="PortfolioIQ" width={36} height={36} className="rounded-lg" />
          </div>
          <div className="font-mono font-bold text-lg tracking-[0.2em]">PORTFOLIOIQ</div>
          <div className="font-mono text-[11px] text-accent/60 mt-1">Create an account</div>
        </div>

        <div className="card p-6 sm:p-8">
          <h1 className="font-mono text-lg font-semibold mb-1">
            <span className="text-accent">{">"}</span> Register
          </h1>
          <p className="font-mono text-xs text-ink-muted mb-6">Welcome to PorfolioIQ</p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="label">first name</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="first name"
                className="input"
              />
            </div>

            <div>
              <label className="label">email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@example.com"
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
                autoComplete="new-password"
                minLength={8}
                placeholder="min 8 characters"
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
                <><Loader2 className="w-4 h-4 animate-spin" /> Creating account</>
              ) : (
                <><UserPlus className="w-4 h-4" /> Register</>
              )}
            </button>
          </form>

          <div className="text-center mt-6 font-mono text-xs text-ink-muted">
            Already have an account ?{" "}
            <Link href="/login" className="text-accent hover:underline">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
