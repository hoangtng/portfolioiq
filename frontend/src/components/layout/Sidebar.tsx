"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, TrendingUp, Eye, Bell, Layers,
  NotebookPen, Sparkles, PieChart, Settings, LogOut,
} from "lucide-react";
import  imageLogo  from "@/static/images/icon.svg"
import Image from "next/image";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";

const PRIMARY = [
  { href: "/dashboard",  label: "Dashboard",  icon: LayoutDashboard },
  { href: "/positions",  label: "Positions",  icon: TrendingUp },
  { href: "/watchlist",  label: "Watchlist",  icon: Eye },
  { href: "/alerts",     label: "Alerts",     icon: Bell },
  { href: "/options",    label: "Options",    icon: Layers },
];

const RESEARCH = [
  { href: "/journal",   label: "Journal",   icon: NotebookPen },
  { href: "/ai",        label: "AI",        icon: Sparkles },
  { href: "/analytics", label: "Analytics", icon: PieChart },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const renderItem = ({ href, label, icon: Icon }: typeof PRIMARY[number]) => {
    const active = pathname === href || pathname.startsWith(href + "/");
    return (
      <Link
        key={href}
        href={href}
        className={cn(
          "flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-mono",
          "transition-all duration-150",
          active
            ? "bg-accent/10 text-accent border-l-2 border-accent pl-[10px]"
            : "text-ink-muted hover:bg-bg-hover hover:text-ink",
        )}
      >
        <Icon className="w-[18px] h-[18px]" strokeWidth={1.5} />
        <span>{label}</span>
      </Link>
    );
  };

  return (
    <aside className="hidden md:flex flex-col w-[240px] shrink-0 bg-bg-rail border-r border-line h-screen sticky top-0">
      {/* Logo */}
      <div className="px-4 pt-6 pb-8">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-accent-gradient flex items-center justify-center font-bold text-bg-deepest text-base shadow-glow">
            <Image src={imageLogo} alt="PortfolioIQ" width={36} height={36} className="rounded-lg" />
          </div>
          <div className="font-mono font-bold text-sm tracking-wider">PORTFOLIOIQ</div>
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 flex flex-col gap-1 overflow-y-auto">
        {PRIMARY.map(renderItem)}

        <div className="text-[10px] font-mono uppercase tracking-wider text-accent/40 px-3 pt-5 pb-2">
          Research
        </div>
        {RESEARCH.map(renderItem)}
      </nav>

      {/* User */}
      <div className="border-t border-line p-3">
        <Link
          href="/settings"
          className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-bg-hover transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-bg-card border border-line-strong flex items-center justify-center font-mono text-xs">
            {user?.email?.slice(0, 1).toUpperCase() ?? "?"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-mono text-[12px] truncate">
              {user?.display_name || user?.email || "anonymous"}
            </div>
            <div className="text-[10px] text-ink-faint font-mono truncate">Settings</div>
          </div>
        </Link>

        <button
          onClick={logout}
          className="mt-2 w-full flex items-center gap-3 px-2 py-2 rounded-lg
                     text-[12px] font-mono text-ink-muted
                     hover:bg-down/10 hover:text-down transition-colors"
        >
          <LogOut className="w-[16px] h-[16px]" strokeWidth={1.5} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
