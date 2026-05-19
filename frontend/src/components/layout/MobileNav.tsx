"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, TrendingUp, Bell, Sparkles, Menu, ChartLine, NotebookPen
} from "lucide-react";
import { cn } from "@/lib/utils";

const ITEMS = [
  { href: "/dashboard",  label: "Home",   icon: LayoutDashboard },
  { href: "/positions",  label: "Positions",   icon: TrendingUp },
  { href: "/analytics",  label: "Analytics",   icon: ChartLine },
  { href: "/journal",     label: "Journals", icon: NotebookPen },
  { href: "/alerts",     label: "Alerts", icon: Bell },
  { href: "/ai",         label: "AI",     icon: Sparkles },
  { href: "/settings",   label: "More",   icon: Menu },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40
                    bg-bg-rail/95 backdrop-blur-xl border-t border-line safe-bottom">
      <div className="flex justify-around items-stretch px-2 py-2">
        {ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-col items-center gap-1 px-3 py-1.5 rounded-lg flex-1",
                "font-mono text-[10px] transition-colors",
                active ? "text-accent" : "text-ink-muted",
              )}
            >
              <Icon className="w-[22px] h-[22px]" strokeWidth={1.5} />
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
