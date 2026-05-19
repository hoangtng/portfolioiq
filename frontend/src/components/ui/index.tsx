"use client";

import { type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── PageHeader ──────────────────────────────────────────────

interface PageHeaderProps {
  title:    string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <header className="flex items-start justify-between gap-4 flex-wrap mb-6">
      <div className="min-w-0">
        <h1 className="font-mono font-bold text-xl sm:text-2xl tracking-tight">
          <span className="text-accent">{">"}</span> {title}
        </h1>
        {subtitle && (
          <p className="font-mono text-xs text-ink-muted mt-1">
            {subtitle}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

// ─── Stat Card ──────────────────────────────────────────────

interface StatCardProps {
  label:     string;
  value:     ReactNode;
  delta?:    ReactNode;
  icon?:     ReactNode;
  featured?: boolean;
  className?: string;
}

export function StatCard({ label, value, delta, icon, featured, className }: StatCardProps) {
  return (
    <div className={cn(featured ? "stat-card card-accent" : "stat-card", className)}>
      <div className="stat-label">
        {icon}
        <span>{label}</span>
      </div>
      <div className={cn("stat-value", featured && "text-accent glow-text")}>{value}</div>
      {delta && <div className="stat-delta">{delta}</div>}
    </div>
  );
}

// ─── Empty State ────────────────────────────────────────────

interface EmptyStateProps {
  icon?:        ReactNode;
  title:        string;
  description?: string;
  action?:      ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="card p-10 text-center flex flex-col items-center gap-3">
      {icon && <div className="text-ink-faint">{icon}</div>}
      <div className="font-mono text-sm text-ink">{title}</div>
      {description && (
        <p className="text-xs text-ink-muted max-w-sm">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

// ─── Modal ──────────────────────────────────────────────────

interface ModalProps {
  open:    boolean;
  onClose: () => void;
  title:   string;
  children: ReactNode;
  width?:  "sm" | "md" | "lg";
}

export function Modal({ open, onClose, title, children, width = "md" }: ModalProps) {
  if (!open) return null;
  const widthClass = width === "sm" ? "max-w-sm" : width === "lg" ? "max-w-2xl" : "max-w-md";

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className={cn(
          "card w-full max-h-[90vh] overflow-y-auto",
          widthClass,
          "shadow-card",
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between px-5 py-4 border-b border-line">
          <h2 className="font-mono font-semibold text-sm tracking-wider">
            <span className="text-accent">{">"}</span> {title}
          </h2>
          <button onClick={onClose} className="btn-icon" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </header>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

// ─── Spinner ────────────────────────────────────────────────

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 font-mono text-xs text-accent">
      <span className="inline-block w-3 h-3 rounded-full bg-accent animate-pulse-glow" />
      <span>{label || "loading"}<span className="cursor-blink"></span></span>
    </div>
  );
}

// ─── Mini Pill ──────────────────────────────────────────────

export function Pill({
  children, tone = "neutral", className,
}: {
  children: ReactNode;
  tone?: "up" | "down" | "cyan" | "warn" | "neutral" | "accent";
  className?: string;
}) {
  const map = {
    up:      "pill-up",
    down:    "pill-down",
    cyan:    "pill-cyan",
    warn:    "pill-warn",
    neutral: "pill-neutral",
    accent:  "bg-accent/10 text-accent pill",
  };
  return <span className={cn(map[tone], className)}>{children}</span>;
}
