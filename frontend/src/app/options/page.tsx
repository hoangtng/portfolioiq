"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Layers } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/ui";

export default function OptionsSearchPage() {
  return (<AppShell><OptionsSearch /></AppShell>);
}

function OptionsSearch() {
  const router = useRouter();
  const [ticker, setTicker] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (ticker.trim()) {
      router.push(`/options/${ticker.trim().toUpperCase()}`);
    }
  };

  const POPULAR = ["SPY", "QQQ", "TSLA", "AAPL", "NVDA", "PLTR", "AMD", "META"];

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[800px] mx-auto">
      <PageHeader
        title="Options"
        subtitle="Research chains · Greeks · IV · Open interest"
      />

      <div className="card p-6 sm:p-8 text-center">
        <Layers className="w-12 h-12 text-accent mx-auto mb-4" strokeWidth={1.5} />
        <h2 className="font-mono text-base mb-2">Research options chain</h2>
        <p className="text-sm text-ink-muted mb-6">
          Look up the full options chain for any ticker — strikes, expiries, Greeks, IV, OI.
        </p>

        <form onSubmit={submit} className="flex gap-2 max-w-md mx-auto">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="enter ticker..."
              className="input pl-10 font-mono"
              autoFocus
            />
          </div>
          <button type="submit" className="btn-primary">
            <Search className="w-4 h-4" /> Chain
          </button>
        </form>

        <div className="mt-8">
          <div className="font-mono text-[10px] uppercase tracking-wider text-ink-faint mb-3">Popular</div>
          <div className="flex gap-2 flex-wrap justify-center">
            {POPULAR.map((t) => (
              <button key={t} onClick={() => router.push(`/options/${t}`)}
                className="px-3 py-1.5 bg-bg-card border border-line rounded-lg font-mono text-xs hover:border-accent/30 hover:text-accent transition-colors">
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
