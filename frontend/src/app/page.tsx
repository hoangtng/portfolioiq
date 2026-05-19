"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import {
  ArrowRight, TrendingUp, Layers, Sparkles, NotebookPen,
  Bell, BarChart3, Check, Activity, Zap, Shield,
  Menu, X, PlayCircle, Gift, Lock, Brain, MessageSquare,
} from "lucide-react";
import image from "@/static/images/icon.svg"
import { useAuth } from "@/lib/auth-context";

export default function LandingPage() {
  const { user, loading } = useAuth();

  return (
    <div className="min-h-screen overflow-x-hidden relative">
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.025]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,255,170,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,170,0.5) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />
      <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed bottom-0 right-1/4 w-[500px] h-[500px] bg-cyan/5 rounded-full blur-[120px] pointer-events-none" />

      <div className="relative z-10">
        <Nav            user={user} loading={loading} />
        <Hero           user={user} loading={loading} />
        <StatsStrip />
        <AISection />
        <ExampleQueries />
        <DemoPreview />
        <FeaturesGrid />
        <HowItWorks />
        <Promise />
        <FinalCTA       user={user} loading={loading} />
        <Footer />
      </div>
    </div>
  );
}

// ─── Nav ───────────────────────────────────────────────────────────

function Nav({ user, loading }: { user: unknown; loading: boolean }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 backdrop-blur-xl bg-bg-deepest/80 border-b border-line">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <Image src={image} alt="PortfolioIQ" width={36} height={36} className="rounded-lg" />
          <span className="font-mono font-bold text-sm tracking-wider">PORTFOLIOIQ</span>
        </Link>

        <div className="hidden md:flex items-center gap-6 font-mono text-xs text-ink-muted">
          <a href="#ai"           className="hover:text-accent transition-colors">AI Analyst</a>
          <a href="#queries"      className="hover:text-accent transition-colors">Examples</a>
          <a href="#features"     className="hover:text-accent transition-colors">Features</a>
          <a href="#promise"      className="hover:text-accent transition-colors">Promise</a>
        </div>

        <div className="hidden md:flex items-center gap-2">
          {loading ? (
            <div className="w-20 h-9 skeleton" />
          ) : user ? (
            <Link href="/dashboard" className="btn-primary text-xs">
              Dashboard <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <>
              <Link href="/login"    className="btn-ghost   text-xs">Sign in</Link>
              <Link href="/register" className="btn-primary text-xs">
                Sign up — it&apos;s free <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </>
          )}
        </div>

        <button onClick={() => setMenuOpen(!menuOpen)} className="md:hidden btn-icon" aria-label="Menu">
          {menuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
        </button>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-line bg-bg-deepest/95 backdrop-blur-xl">
          <div className="px-4 py-4 flex flex-col gap-3 font-mono text-sm">
            <a href="#ai"       onClick={() => setMenuOpen(false)} className="text-ink-muted hover:text-accent">AI Analyst</a>
            <a href="#queries"  onClick={() => setMenuOpen(false)} className="text-ink-muted hover:text-accent">Examples</a>
            <a href="#features" onClick={() => setMenuOpen(false)} className="text-ink-muted hover:text-accent">Features</a>
            <a href="#promise"  onClick={() => setMenuOpen(false)} className="text-ink-muted hover:text-accent">Promise</a>
            <div className="border-t border-line pt-3 flex flex-col gap-2">
              {user ? (
                <Link href="/dashboard" className="btn-primary">Dashboard <ArrowRight className="w-4 h-4" /></Link>
              ) : (
                <>
                  <Link href="/login"    className="btn-secondary">Sign in</Link>
                  <Link href="/register" className="btn-primary">Sign up — it&apos;s free</Link>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}

 //─── Hero ──────────────────────────────────────────────────────────

function Hero({ user, loading }: { user: unknown; loading: boolean }) {
  return (
    <section className="px-4 sm:px-6 lg:px-8 pt-16 pb-20 sm:pt-24 sm:pb-28">
      <div className="max-w-[1280px] mx-auto">

        <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 rounded-full bg-bg-card border border-line-strong">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-glow" />
          <span className="font-mono text-[11px] tracking-wider text-ink-dim">
             powered by AI
          </span>
        </div>

        <h1 className="font-mono font-bold text-4xl sm:text-5xl lg:text-6xl xl:text-7xl tracking-tight leading-[1.05] max-w-4xl">
          <span className="text-accent glow-text">{">"}</span>{" "}
          An AI analyst
          <br />
          <span className="text-ink-dim">that actually knows</span>{" "}
          <span className="blink-text"></span>
          <span className="cursor-blink text-accent"></span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-ink-dim max-w-2xl font-sans leading-relaxed">
          Ask anything about your positions. Get expert-level analysis
          grounded in your real holdings — not a generic chatbot reading
          headlines. Powered by AI.
        </p>

        <div className="mt-10 flex flex-wrap items-center gap-3">
          {loading ? (
            <div className="w-40 h-12 skeleton rounded-lg" />
          ) : user ? (
            <Link href="/dashboard" className="btn-primary text-base py-3 px-5">
              Go to dashboard <ArrowRight className="w-4 h-4" />
            </Link>
          ) : (
            <>
              <Link href="/register" className="btn-primary text-base py-3 px-5">
                Sign up — it&apos;s free <ArrowRight className="w-4 h-4" />
              </Link>
              <a href="#demo" className="btn-secondary text-base py-3 px-5">
                <PlayCircle className="w-4 h-4" /> Watch demo
              </a>
            </>
          )}
        </div>

        <div className="mt-12 flex flex-wrap gap-x-6 gap-y-2 font-mono text-xs text-ink-faint">
          <span className="inline-flex items-center gap-1.5"><Check className="w-3 h-3 text-accent" /> Free</span>
          <span className="inline-flex items-center gap-1.5"><Check className="w-3 h-3 text-accent" /> Powered by AI</span>
          <span className="inline-flex items-center gap-1.5"><Check className="w-3 h-3 text-accent" /> Ad-free</span>
          <span className="inline-flex items-center gap-1.5"><Check className="w-3 h-3 text-accent" /> Your data stays yours</span>
        </div>
      </div>
    </section>
  );
}

 //─── Stats strip ───────────────────────────────────────────────────

function StatsStrip() {
  const stats = [
    { value: "12,000+", label: "AI analyses delivered" },
    { value: "1,200+",  label: "active traders" },
    { value: "$87M",    label: "positions tracked" },
    { value: "99.9%",   label: "uptime" },
  ];
  return (
    <section className="px-4 sm:px-6 lg:px-8 py-8 border-y border-line bg-bg-rail/30">
      <div className="max-w-[1280px] mx-auto grid grid-cols-2 sm:grid-cols-4 gap-6">
        {stats.map((s) => (
          <div key={s.label} className="text-center">
            <div className="font-mono font-bold text-2xl sm:text-3xl text-accent glow-text">
              {s.value}
            </div>
            <div className="font-mono text-[11px] text-ink-faint uppercase tracking-wider mt-1">
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── AI section ────────────────────────────────────────────────────

function AISection() {
  return (
    <section id="ai" className="px-4 sm:px-6 lg:px-8 py-20 sm:py-24 relative">
      <div className="max-w-[1280px] mx-auto">

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">

          <div>
            <div className="section-title mb-3"> AI Analyst</div>
            <h2 className="font-mono font-bold text-3xl sm:text-4xl tracking-tight mb-4">
              <span className="text-accent">{"> "}</span> Generic chatbots can&apos;t see your portfolio. Ours can.
            </h2>
            <p className="text-ink-dim text-lg leading-relaxed mb-6">
              Most AI tools live in a vacuum — you copy your positions,
              hope for the best. PortfolioIQ wires AI directly into your
              live portfolio data, so every answer is grounded in your real
              holdings, real costs, real exposure.
            </p>

            <ul className="flex flex-col gap-4">
              <AIBullet icon={Brain} title="One-click portfolio analysis">
                Concentration risk. Expiry exposure. Specific rebalancing
                suggestions for your book. A full analyst memo in seconds.
              </AIBullet>
              <AIBullet icon={NotebookPen} title="Auto-journal every trade">
                Hand it a trade, it writes the structured entry — title,
                thesis, risk factors, plan. Tagged and searchable from day one.
              </AIBullet>
              <AIBullet icon={MessageSquare} title="Conversational follow-ups">
                Ask anything. The AI keeps the full context of your portfolio
                and remembers what you discussed earlier in the chat.
              </AIBullet>
            </ul>
          </div>

          <div className="card p-5 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="section-title"> Portfolio chat</div>
              <div className="font-mono text-[10px] text-ink-faint flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-glow" />
                live
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <ChatBubble role="user">What&apos;s my biggest concentration risk?</ChatBubble>
              <ChatBubble role="assistant">
                Your <strong className="text-accent">PLTR call position</strong> is{" "}
                <strong>34% of portfolio value</strong> — well above a healthy
                20-25% cap. The July 18 expiry adds time-decay risk too.
                <br /><br />
                Consider: roll half to October at the $170 strike to reduce
                theta exposure, or trim 30% to lock in the current +30% gain.
              </ChatBubble>
              <ChatBubble role="user">How exposed am I to tech?</ChatBubble>
              <ChatBubble role="assistant">
                <strong>76%</strong> of your portfolio is in tech (PLTR, NVDA,
                AAPL, AMD). That&apos;s heavy sector concentration. Adding XLE
                or GLD could give you some non-correlation insurance.
              </ChatBubble>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function AIBullet({ icon: Icon, title, children }: {
  icon: typeof Activity; title: string; children: React.ReactNode;
}) {
  return (
    <li className="flex gap-3">
      <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0">
        <Icon className="w-4 h-4 text-accent" strokeWidth={1.75} />
      </div>
      <div>
        <div className="font-mono text-sm font-semibold mb-1">{title}</div>
        <p className="text-sm text-ink-dim leading-relaxed">{children}</p>
      </div>
    </li>
  );
}

function ChatBubble({ role, children }: { role: "user" | "assistant"; children: React.ReactNode }) {
  const isUser = role === "user";
  return (
    <div className={`max-w-[88%] ${isUser ? "ml-auto" : ""}`}>
      <div className={`p-3 rounded-lg text-sm ${
        isUser
          ? "bg-accent/10 border border-accent/20 text-ink"
          : "bg-bg-deepest border border-line text-ink-dim"
      }`}>
        {children}
      </div>
    </div>
  );
}

 //─── Example queries — what you can ask ────────────────────────────

function ExampleQueries() {
  const queries = [
    { q: "What's my biggest concentration risk right now?",   tag: "Risk" },
    { q: "Should I roll my July PLTR calls to October?",       tag: "Options" },
    { q: "How exposed am I to tech?",                          tag: "Allocation" },
    { q: "Did I overtrade this month? Show me the data.",     tag: "Behavior" },
    { q: "What's a smart entry point for NVDA?",               tag: "Timing" },
    { q: "Compare my Q3 to Q4 performance.",                   tag: "Stats" },
  ];

  return (
    <section id="queries" className="px-4 sm:px-6 lg:px-8 py-20 sm:py-24">
      <div className="max-w-[1280px] mx-auto">
        <header className="mb-10 text-center">
          <div className="section-title mb-3"> Example questions</div>
          <h2 className="font-mono font-bold text-3xl sm:text-4xl tracking-tight mb-3">
            <span className="text-accent">{">"}</span> Just ask - it knows your book.
          </h2>
          <p className="text-ink-dim max-w-xl mx-auto">
            Real questions from real traders. Every answer grounded in your
            live holdings — not a generic web search dressed up as advice.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-4xl mx-auto">
          {queries.map((item) => (
            <Link
              key={item.q}
              href="/register"
              className="card-hover p-4 sm:p-5 group flex items-center gap-3 hover:border-accent/40 transition-colors"
            >
              <div className="w-9 h-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0 group-hover:bg-accent/20 transition-colors">
                <Sparkles className="w-4 h-4 text-accent" strokeWidth={1.75} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-ink-dim group-hover:text-ink transition-colors mb-1">
                  &ldquo;{item.q}&rdquo;
                </div>
                <div className="font-mono text-[10px] text-ink-faint uppercase tracking-wider">
                   {item.tag.toLowerCase()}
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-ink-faint group-hover:text-accent transition-colors flex-shrink-0" />
            </Link>
          ))}
        </div>

        <div className="mt-8 text-center">
          <p className="font-mono text-xs text-ink-faint mb-3">
             and a thousand others, in plain English
          </p>
          <Link href="/register" className="btn-primary text-sm">
            Try it — it&apos;s free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}

 //─── Demo preview ──────────────────────────────────────────────────

function DemoPreview() {
  return (
    <section id="demo" className="px-4 sm:px-6 lg:px-8 py-20">
      <div className="max-w-[1280px] mx-auto">

        <header className="mb-10 text-center">
          <div className="section-title mb-3"> Dashboard</div>
          <h2 className="font-mono font-bold text-3xl sm:text-4xl tracking-tight">
            <span className="text-accent">{">"}</span> the AI lives where your portfolio does
          </h2>
        </header>

        <div className="rounded-2xl border border-line-strong bg-bg-rail shadow-2xl shadow-accent/5 overflow-hidden">

          <div className="flex items-center gap-2 px-4 py-3 border-b border-line">
            <div className="w-3 h-3 rounded-full bg-down/60" />
            <div className="w-3 h-3 rounded-full bg-warn/60" />
            <div className="w-3 h-3 rounded-full bg-up/60" />
            <div className="ml-4 font-mono text-[10px] text-ink-faint truncate">
              app.portfolioiq.com/dashboard
            </div>
          </div>

          <div className="p-4 sm:p-8 bg-bg-base">
            <div className="flex items-start justify-between mb-6 flex-wrap gap-2">
              <div>
                <div className="font-mono font-bold text-xl">
                  <span className="text-accent">{">"}</span> ethan<span className="cursor-blink"></span>
                </div>
                <div className="font-mono text-[11px] text-ink-muted mt-1">
                   Tuesday, Nov 11 · <span className="text-up">market_open</span> · 14:23 NY
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
              <MockStat featured label="Portfolio"      value="$47,283" delta="+$1,247 (+2.71%)" up />
              <MockStat         label="Open positions"  value="12"      delta="$28,540 invested"   />
              <MockStat         label="Cost basis"      value="$46.0k"  delta="total deployed"     />
              <MockStat         label="Status"          value="LIVE"    delta="prices_cached"      />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-3">
              <div className="card p-4 sm:p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="section-title"> P&L history</div>
                  <div className="font-mono text-[10px] text-ink-faint">30d</div>
                </div>
                <Sparkline />
              </div>

              <div className="card p-4">
                <div className="section-title mb-3"> Top positions</div>
                <div className="flex flex-col">
                  <MockPosition ticker="PLTR" type="CALL" qty="2 @ $4.50"  price="$5.85"  pnl="+$270" pnlPct="+30%"   up />
                  <MockPosition ticker="NVDA"           qty="10 @ $920"  price="$945"   pnl="+$250" pnlPct="+2.7%"  up />
                  <MockPosition ticker="TSLA"           qty="5 @ $235"   price="$218"   pnl="-$85"  pnlPct="-7.2%"     />
                  <MockPosition ticker="AAPL"           qty="15 @ $185"  price="$192"   pnl="+$105" pnlPct="+3.8%"  up />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function MockStat({ label, value, delta, featured, up }: {
  label: string; value: string; delta: string; featured?: boolean; up?: boolean;
}) {
  return (
    <div className={featured ? "stat-card card-accent" : "stat-card"}>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${featured ? "text-accent glow-text" : ""}`}>{value}</div>
      <div className={`stat-delta ${up ? "text-up" : "text-ink-muted"}`}>{delta}</div>
    </div>
  );
}

function MockPosition({ ticker, type, qty, price, pnl, pnlPct, up }: {
  ticker: string; type?: string; qty: string; price: string; pnl: string; pnlPct: string; up?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 py-2 border-t border-line first:border-t-0">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center font-mono font-bold text-[10px] border ${
        up ? "bg-up/15 text-up border-up/30" : "bg-down/15 text-down border-down/30"
      }`}>{ticker.slice(0, 4)}</div>
      <div className="flex-1 min-w-0">
        <div className="font-mono font-semibold text-xs flex items-center gap-1.5">
          {ticker}
          {type && <span className="pill-cyan">{type}</span>}
        </div>
        <div className="font-mono text-[10px] text-ink-faint">{qty}</div>
      </div>
      <div className="text-right">
        <div className="font-mono text-xs">{price}</div>
        <div className={`font-mono text-[10px] ${up ? "text-up" : "text-down"}`}>{pnl} · {pnlPct}</div>
      </div>
    </div>
  );
}

function Sparkline() {
  return (
    <svg viewBox="0 0 600 160" className="w-full h-32" preserveAspectRatio="none">
      <defs>
        <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#00FFAA" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#00FFAA" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d="M 0 120 L 30 115 L 60 100 L 90 105 L 120 90 L 150 85 L 180 95 L 210 70 L 240 75 L 270 60 L 300 65 L 330 55 L 360 70 L 390 50 L 420 45 L 450 30 L 480 40 L 510 25 L 540 35 L 570 20 L 600 25 L 600 160 L 0 160 Z"
        fill="url(#lineGrad)" />
      <path
        d="M 0 120 L 30 115 L 60 100 L 90 105 L 120 90 L 150 85 L 180 95 L 210 70 L 240 75 L 270 60 L 300 65 L 330 55 L 360 70 L 390 50 L 420 45 L 450 30 L 480 40 L 510 25 L 540 35 L 570 20 L 600 25"
        stroke="#00FFAA" strokeWidth="2" fill="none" />
      <circle cx="600" cy="25" r="4" fill="#00FFAA" />
      <circle cx="600" cy="25" r="8" fill="#00FFAA" opacity="0.3" className="animate-pulse-glow" />
    </svg>
  );
}

 //─── Features (secondary — supporting cast for the AI) ─────────────

function FeaturesGrid() {
  const features = [
    {
      icon:  TrendingUp,
      title: "Live position tracking",
      desc:  "Real-time P&L on every stock and option, refreshed every 15 seconds. The AI sees the same data you do.",
    },
    {
      icon:  Layers,
      title: "Pro-grade options data",
      desc:  "Full chains for any ticker with IV, OI, and every Greek. Break-even auto-computed. Feeds straight into the AI.",
    },
    {
      icon:  NotebookPen,
      title: "Smart trade journal",
      desc:  "AI writes a structured entry for every trade. Searchable history with tags and P&L attribution.",
    },
    {
      icon:  Bell,
      title: "Instant alerts",
      desc:  "Set price targets in seconds. Telegram or email ping the moment your level hits.",
    },
    {
      icon:  BarChart3,
      title: "Performance analytics",
      desc:  "Win rate, profit factor, allocation breakdowns. Spot what's actually working in your trading.",
    },
    {
      icon:  Zap,
      title: "Built for speed",
      desc:  "Polls every 20 seconds. Pauses when you're not looking. Won't drain your laptop battery.",
    },
  ];

  return (
    <section id="features" className="px-4 sm:px-6 lg:px-8 py-20 sm:py-24">
      <div className="max-w-[1280px] mx-auto">
        <header className="mb-12">
          <div className="section-title mb-3"> What else you get</div>
          <h2 className="font-mono font-bold text-3xl sm:text-4xl tracking-tight">
            <span className="text-accent">{">"}</span> the AI is the headline. these make it sharper.
          </h2>
          <p className="mt-3 text-ink-dim max-w-2xl">
            Every feature feeds the AI better data. Better data, better answers.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((f) => (
            <div key={f.title} className="card-hover p-6 group">
              <div className="w-10 h-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                <f.icon className="w-5 h-5 text-accent" strokeWidth={1.75} />
              </div>
              <h3 className="font-mono font-semibold text-base mb-2">{f.title}</h3>
              <p className="text-sm text-ink-dim leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

 //─── How it works ──────────────────────────────────────────────────

function HowItWorks() {
  const steps = [
    {
      n: "01",
      title: "Add your positions",
      desc:  "Manual entry or CSV import. Stocks and option contracts welcome. Takes under a minute.",
    },
    {
      n: "02",
      title: "Ask the AI anything",
      desc:  "Click analyze for a full memo. Or just type a question. The AI sees your whole portfolio in real time.",
    },
    {
      n: "03",
      title: "Trade smarter every day",
      desc:  "Set alerts. Journal your trades. Iterate on the strategies that work. Drop the ones that don't.",
    },
  ];

  return (
    <section id="how-it-works" className="px-4 sm:px-6 lg:px-8 py-20 sm:py-24">
      <div className="max-w-[1280px] mx-auto">
        <header className="mb-12 text-center">
          <div className="section-title mb-3"> How it works</div>
          <h2 className="font-mono font-bold text-3xl sm:text-4xl tracking-tight">
            <span className="text-accent">{">"}</span> Three steps to a smarter portfolio
          </h2>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative">
          <div className="hidden md:block absolute top-12 left-[16.6%] right-[16.6%] h-px bg-gradient-to-r from-transparent via-accent/30 to-transparent" />

          {steps.map((step) => (
            <div key={step.n} className="card p-6 relative">
              <div className="font-mono text-[40px] text-accent/20 font-bold leading-none mb-4">
                {step.n}
              </div>
              <h3 className="font-mono font-semibold text-base mb-2">{step.title}</h3>
              <p className="text-sm text-ink-dim leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

 //─── Our promise ───────────────────────────────────────────────────

function Promise() {
  const promises = [
    {
      icon:  Gift,
      title: "Free",
      desc:  "Every feature, fully unlocked. No paywalls, no upsells, no credit card. If we ever introduce paid plans, you'll have plenty of notice — early users will always have a path forward.",
    },
    {
      icon:  Shield,
      title: "Ad-free",
      desc:  "We don't sell your attention. Your dashboard stays clean. Your inbox stays clean. The only thing you'll see on the screen is your portfolio.",
    },
    {
      icon:  Lock,
      title: "Private",
      desc:  "Bank-level encryption at rest. Never sold to third parties. Never shared. Export everything anytime. Delete your account and we erase it all.",
    },
  ];

  return (
    <section id="promise" className="px-4 sm:px-6 lg:px-8 py-20 sm:py-24">
      <div className="max-w-[1280px] mx-auto">
        <header className="mb-12 text-center">
          <div className="section-title mb-3"> Our promise</div>
          <h2 className="font-mono font-bold text-3xl sm:text-4xl tracking-tight mb-3">
            <span className="text-accent">{">"}</span> Built for traders, not advertisers
          </h2>
          <p className="text-ink-dim max-w-xl mx-auto">
            Free. Ad-free. Private. Three commitments — read them twice.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {promises.map((p) => (
            <div
              key={p.title}
              className="card p-6 sm:p-8 relative overflow-hidden group hover:border-accent/30 transition-colors"
            >
              <div className="w-12 h-12 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center mb-5">
                <p.icon className="w-6 h-6 text-accent" strokeWidth={1.75} />
              </div>
              <h3 className="font-mono font-bold text-lg mb-3">{p.title}</h3>
              <p className="text-sm text-ink-dim leading-relaxed">{p.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

 //─── Final CTA ─────────────────────────────────────────────────────

function FinalCTA({ user, loading }: { user: unknown; loading: boolean }) {
  return (
    <section className="px-4 sm:px-6 lg:px-8 py-20 sm:py-28">
      <div className="max-w-[900px] mx-auto">
        <div className="card-accent p-8 sm:p-12 text-center">
          <Sparkles className="w-10 h-10 text-accent mx-auto mb-4" strokeWidth={1.5} />
          <h2 className="font-mono font-bold text-3xl sm:text-4xl tracking-tight mb-3">
            <span className="text-accent">{">"}</span> Meet your AI analyst.
          </h2>
          <p className="text-ink-dim max-w-lg mx-auto mb-8">
            Sign up free. Add your positions. Ask the AI anything.
            Takes 30 seconds. No credit card. No catches.
          </p>

          {loading ? (
            <div className="w-40 h-12 skeleton rounded-lg mx-auto" />
          ) : user ? (
            <Link href="/dashboard" className="btn-primary text-base py-3 px-6">
              Go to dashboard <ArrowRight className="w-4 h-4" />
            </Link>
          ) : (
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link href="/register" className="btn-primary text-base py-3 px-6">
                Sign up — it&apos;s free <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="/login" className="btn-ghost text-base py-3 px-5">
                Already a member? Sign in
              </Link>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

 //─── Footer ────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-7 h-7 rounded-md bg-accent-gradient flex items-center justify-center font-bold text-bg-deepest text-xs">P</div>
              <span className="font-mono font-bold text-sm tracking-wider">PORTFOLIOIQ</span>
            </div>
            <p className="text-xs text-ink-faint">
              An AI analyst that actually knows your portfolio. Free, ad-free, private.
            </p>
          </div>

          <div>
            <div className="font-mono text-[11px] uppercase tracking-wider text-ink-muted mb-3">Product</div>
            <ul className="flex flex-col gap-2 text-xs text-ink-dim">
              <li><a href="#ai"        className="hover:text-accent">AI Analyst</a></li>
              <li><a href="#queries"   className="hover:text-accent">Examples</a></li>
              <li><a href="#features"  className="hover:text-accent">Features</a></li>
              <li><Link href="/login"  className="hover:text-accent">Sign in</Link></li>
            </ul>
          </div>

          <div>
            <div className="font-mono text-[11px] uppercase tracking-wider text-ink-muted mb-3">Company</div>
            <ul className="flex flex-col gap-2 text-xs text-ink-dim">
              <li><a href="#" className="hover:text-accent">About</a></li>
              <li><a href="#" className="hover:text-accent">Blog</a></li>
              <li><a href="#" className="hover:text-accent">Changelog</a></li>
              <li><a href="#" className="hover:text-accent">Contact</a></li>
            </ul>
          </div>

          <div>
            <div className="font-mono text-[11px] uppercase tracking-wider text-ink-muted mb-3">Legal</div>
            <ul className="flex flex-col gap-2 text-xs text-ink-dim">
              <li><a href="#" className="hover:text-accent">Privacy policy</a></li>
              <li><a href="#" className="hover:text-accent">Terms of service</a></li>
              <li><a href="#" className="hover:text-accent">Security</a></li>
              <li><a href="#" className="hover:text-accent">Disclaimers</a></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-line pt-6 flex flex-wrap items-center justify-between gap-3">
          <div className="font-mono text-[11px] text-ink-faint">
            © 2026 PortfolioIQ. All rights reserved.
          </div>
          <div className="font-mono text-[11px] text-ink-faint">
             Not investment advice. Trading involves risk of loss.
          </div>
        </div>
      </div>
    </footer>
  );
}
