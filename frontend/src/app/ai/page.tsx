"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Loader2, Sparkles, NotebookPen, ChartArea, RefreshCw } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader, Pill } from "@/components/ui";
import { ai, ApiError } from "@/lib/api";

interface ChatMessage {
  role:    "user" | "assistant" | "system";
  content: string;
}

export default function AIPage() {
  return (<AppShell><AIWorkbench /></AppShell>);
}

function AIWorkbench() {
  const [tab, setTab] = useState<"chat" | "analyze" | "journal">("chat");

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1100px] mx-auto">
      <PageHeader title="AI" subtitle="AI powered · Portfolio context · Trade journal writer" />

      {/* Tabs */}
      <div className="flex gap-1 bg-bg-card border border-line rounded-lg p-1 mb-6 max-w-md">
        {([
          { id: "chat",    label: "Chat",    icon: Sparkles },
          { id: "analyze", label: "Analyze", icon: ChartArea },
          { id: "journal", label: "Journal", icon: NotebookPen },
        ] as const).map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-mono rounded ${
              tab === id ? "bg-accent/10 text-accent" : "text-ink-muted"
            }`}>
            <Icon className="w-3.5 h-3.5" /> {label}
          </button>
        ))}
      </div>

      {tab === "chat"    && <ChatTab />}
      {tab === "analyze" && <AnalyzeTab />}
      {tab === "journal" && <JournalGenTab />}
    </div>
  );
}

// ─── Chat tab ────────────────────────────────────────────────

function ChatTab() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput]       = useState("");
  const [busy, setBusy]         = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setBusy(true);

    try {
      // Build history from current messages (exclude system error messages)
      const history = [...messages, userMsg]
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));
      const resp = await ai.chat(text, history);
      setMessages((m) => [...m, { role: "assistant", content: resp.answer }]);
    } catch (e) {
      setMessages((m) => [...m, {
        role: "system",
        content: e instanceof ApiError ? `! ${e.message}` : "! Chat failed",
      }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="card">
      <div className="px-5 py-4 border-b border-line">
        <h3 className="section-title">Portfolio chat</h3>
        <p className="text-[11px] text-ink-muted font-mono mt-1">AI has your live portfolio context</p>
      </div>

      <div className="p-5 min-h-[400px] max-h-[60vh] overflow-y-auto flex flex-col gap-4">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <Sparkles className="w-10 h-10 text-accent mx-auto mb-3" strokeWidth={1.5} />
            <h3 className="font-mono text-sm mb-2"> Chat with AI</h3>
            <p className="text-xs text-ink-muted max-w-sm mx-auto mb-6">
              Ask anything about your positions, Greeks, market conditions, or strategy.
            </p>
            <div className="flex gap-2 flex-wrap justify-center">
              {[
                "What's my biggest concentration risk?",
                "Which options expire soonest?",
                "How exposed am I to tech?",
              ].map((q) => (
                <button key={q} onClick={() => setInput(q)}
                  className="px-3 py-1.5 bg-bg-card border border-line rounded-lg text-xs hover:border-accent/30 hover:text-accent transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`max-w-[80%] ${m.role === "user" ? "ml-auto" : ""}`}>
              <div className={`p-3 rounded-lg text-sm ${
                m.role === "user"
                  ? "bg-accent/10 border border-accent/20 text-ink"
                  : m.role === "system"
                  ? "bg-down/10 border border-down/20 text-down font-mono"
                  : "bg-bg-card border border-line text-ink-dim"
              }`}>
                {m.role === "assistant" ? (
                  <div className="prose prose-invert prose-sm max-w-none font-sans">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
              </div>
            </div>
          ))
        )}
        {busy && (
          <div className="max-w-[80%]">
            <div className="p-3 rounded-lg bg-bg-card border border-line">
              <div className="flex items-center gap-2 text-xs font-mono text-accent">
                <div className="w-2 h-2 rounded-full bg-accent animate-pulse-glow" />
                thinking
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={send} className="p-4 border-t border-line flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="ask AI..." className="input flex-1" disabled={busy} />
        <button type="submit" disabled={busy || !input.trim()} className="btn-primary">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </form>
    </div>
  );
}

// ─── Analyze tab ────────────────────────────────────────────

function AnalyzeTab() {
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setBusy(true); setError(""); setAnalysis(null);
    try {
      const { task_id } = await ai.analyze();
      const result = await ai.pollTask(task_id);
      if (result.status === "success" && result.data.status === "ok")
        setAnalysis(result.data.response);
      else if (result.status === "failure")
        setError(result.error);
      else if (result.status === "success" && result.data.status === "error")
        setError(result.data.error);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Analysis failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="card p-5 sm:p-8">
      <div className="text-center mb-6">
        <ChartArea className="w-12 h-12 text-accent mx-auto mb-3" strokeWidth={1.5} />
        <h3 className="font-mono text-base mb-2">Portfolio analyst</h3>
        <p className="text-sm text-ink-muted max-w-md mx-auto">
          AI reviews your open positions, finds concentration risk, expiry risk, and suggests next steps.
        </p>
        <button onClick={run} disabled={busy} className="btn-primary mt-4">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {busy ? "analyzing (this takes ~30s)" : "run analysis"}
        </button>
      </div>

      {error && (
        <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg">! {error}</div>
      )}

      {analysis && (
        <div className="pt-6 border-t border-line">
          <div className="prose prose-invert prose-ai prose-sm sm:prose-base max-w-none font-sans">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis}</ReactMarkdown>
          </div>
          <button onClick={run} disabled={busy} className="btn-secondary mt-6">
            <RefreshCw className="w-3.5 h-3.5" /> re-run
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Generate journal tab ───────────────────────────────────

function JournalGenTab() {
  const [ticker, setTicker]     = useState("");
  const [thesis, setThesis]     = useState("");
  const [strategy, setStrategy] = useState("");
  const [busy, setBusy]         = useState(false);
  const [result, setResult]     = useState<string | null>(null);
  const [savedId, setSavedId]   = useState<number | null>(null);
  const [error, setError]       = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(""); setResult(null);
    try {
      const { task_id } = await ai.generateJournal({ ticker, thesis, strategy });
      const r = await ai.pollTask(task_id);
      if (r.status === "success" && r.data.status === "ok") {
        setResult(r.data.response);
        if (r.data.saved_entry_id) setSavedId(r.data.saved_entry_id);
      } else if (r.status === "failure")
        setError(r.error);
      else if (r.status === "success" && r.data.status === "error")
        setError(r.data.error);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Generation failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="card p-5 sm:p-8">
      <div className="mb-6 text-center">
        <NotebookPen className="w-10 h-10 text-accent mx-auto mb-3" strokeWidth={1.5} />
        <h3 className="font-mono text-base">Generate journal entry</h3>
        <p className="text-sm text-ink-muted mt-2 max-w-md mx-auto">
          Give AI your ticker and thesis. It writes a structured journal entry and saves it for you.
        </p>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-4 max-w-md mx-auto">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">ticker</label>
            <input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
              required placeholder="PLTR" className="input font-mono" />
          </div>
          <div>
            <label className="label">strategy (optional)</label>
            <input value={strategy} onChange={(e) => setStrategy(e.target.value)}
              placeholder="long 160 calls jul 18" className="input" />
          </div>
        </div>

        <div>
          <label className="label">thesis</label>
          <textarea value={thesis} onChange={(e) => setThesis(e.target.value)}
            required rows={4} className="input resize-none"
            placeholder="Why are you interested? What's your conviction?" />
        </div>

        {error && <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg">! {error}</div>}

        <button type="submit" disabled={busy} className="btn-primary">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {busy ? "generating (~20s)" : "Generate"}
        </button>
      </form>

      {result && (
        <div className="mt-8 pt-6 border-t border-line max-w-2xl mx-auto">
          {savedId && (
            <Pill tone="accent" className="mb-4">
              <Sparkles className="w-2.5 h-2.5" /> saved as entry #{savedId}
            </Pill>
          )}
          <div className="prose prose-invert prose-sm sm:prose-base max-w-none font-sans">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
