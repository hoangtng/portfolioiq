"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, Trash2, Loader2, Edit2, Save, X, Sparkles } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { Spinner, Pill } from "@/components/ui";
import { journal as journalApi, ApiError } from "@/lib/api";
import { fmtDate } from "@/lib/utils";
import type { JournalEntry } from "@/types";

export default function JournalDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const parsed = parseInt(id, 10);
  if (isNaN(parsed)) return <AppShell><div className="p-8 font-mono text-down">// invalid_entry_id</div></AppShell>;
  return (<AppShell><Detail id={parsed} /></AppShell>);
}

function Detail({ id }: { id: number }) {
  const router = useRouter();
  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);

  const [title, setTitle] = useState("");
  const [body, setBody]   = useState("");

  const load = async () => {
    setLoadError("");
    try {
      const data = await journalApi.get(id);
      setEntry(data);
      setTitle(data.title);
      setBody(data.body);
    } catch (e) {
      setLoadError(e instanceof ApiError ? e.message : "Failed to load entry");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);

  const onSave = async () => {
    setSaveError(""); setBusy(true);
    try {
      await journalApi.update(id, { title, body });
      setEditing(false);
      load();
    } catch (e) {
      setSaveError(e instanceof ApiError ? e.message : "Failed to save");
    } finally { setBusy(false); }
  };

  const onDelete = async () => {
    if (!confirm("Delete this entry?")) return;
    setBusy(true);
    try {
      await journalApi.delete(id);
      router.push("/journal");
    } catch (e) { console.error(e); }
    finally { setBusy(false); }
  };

  if (loading) return <div className="p-8 flex items-center justify-center"><Spinner /></div>;
  if (loadError) return (
    <div className="p-8 font-mono text-down text-sm">
      ! {loadError}
      <button onClick={load} className="ml-3 underline hover:text-down/80">retry</button>
    </div>
  );
  if (!entry) return <div className="p-8 font-mono text-down">// entry_not_found</div>;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[800px] mx-auto">
      <Link href="/journal" className="inline-flex items-center gap-2 font-mono text-xs text-ink-muted hover:text-accent mb-4">
        <ArrowLeft className="w-4 h-4" /> back to Journal
      </Link>

      <div className="card p-6 sm:p-8">
        {/* Meta */}
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          {entry.ticker && <Pill tone="cyan">{entry.ticker}</Pill>}
          {entry.ai_generated && <Pill tone="accent"><Sparkles className="w-2.5 h-2.5" /> ai_generated</Pill>}
          {entry.tags.map((t) => <Pill key={t} tone="neutral">{t}</Pill>)}
          <div className="ml-auto font-mono text-[11px] text-ink-faint">
            {fmtDate(entry.created_at, "long")}
          </div>
        </div>

        {/* Title / body */}
        {editing ? (
          <>
            <input value={title} onChange={(e) => setTitle(e.target.value)}
              className="input text-xl font-semibold mb-4" />
            <textarea value={body} onChange={(e) => setBody(e.target.value)}
              rows={16} className="input resize-y leading-relaxed" />
          </>
        ) : (
          <>
            <h1 className="text-2xl sm:text-3xl font-bold mb-6 tracking-tight">{entry.title}</h1>
            <div className="prose prose-invert prose-sm sm:prose-base max-w-none font-sans leading-relaxed text-ink-dim">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.body}</ReactMarkdown>
            </div>
          </>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-3 mt-8 pt-6 border-t border-line">
          {saveError && (
            <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg">! {saveError}</div>
          )}
          <div className="flex gap-2">
            {editing ? (
              <>
                <button onClick={onSave} disabled={busy} className="btn-primary">
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  save
                </button>
                <button onClick={() => { setEditing(false); setSaveError(""); setTitle(entry.title); setBody(entry.body); }} className="btn-secondary">
                  <X className="w-4 h-4" /> cancel
                </button>
              </>
            ) : (
              <>
                <button onClick={() => setEditing(true)} className="btn-secondary">
                  <Edit2 className="w-4 h-4" /> edit
                </button>
                <button onClick={onDelete} disabled={busy} className="btn-icon hover:text-down hover:border-down/30">
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
