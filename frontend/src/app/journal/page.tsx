"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Search, Loader2, Sparkles, NotebookPen } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader, Modal, EmptyState, Spinner, Pill } from "@/components/ui";
import { journal as journalApi, ApiError } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import type { JournalEntry, JournalSearchResponse } from "@/types";

/** Allow only <mark> tags — strips every other HTML to prevent XSS. */
function sanitizeHighlight(html: string): string {
  return html
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/&lt;mark&gt;/g, "<mark>")
    .replace(/&lt;\/mark&gt;/g, "</mark>");
}

export default function JournalPage() {
  return (<AppShell><JournalList /></AppShell>);
}

function JournalList() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [search, setSearch]   = useState<JournalSearchResponse | null>(null);
  const [query, setQuery]     = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError]     = useState("");
  const [searchError, setSearchError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  const load = async () => {
    setLoading(true); setLoadError("");
    try {
      const data = await journalApi.list();
      setEntries(data.results);
    } catch (e) {
      setLoadError(e instanceof ApiError ? e.message : "Failed to load entries");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  // Debounced search
  useEffect(() => {
    const q = query.trim();
    if (!q) { setSearch(null); setSearchError(""); return; }
    const t = setTimeout(async () => {
      setSearchError("");
      try {
        const data = await journalApi.search({ q });
        setSearch(data);
      } catch (e) {
        setSearchError(e instanceof ApiError ? e.message : "Search failed");
      }
    }, 350);
    return () => clearTimeout(t);
  }, [query]);

  const displayed = search ? search.results : entries;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[1100px] mx-auto">
      <PageHeader
        title="Journal"
        subtitle="Trade notes · Research · AI generated entries"
        actions={
          <button onClick={() => setModalOpen(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> New entry
          </button>
        }
      />

      {/* Search */}
      <div className="relative mb-4">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="search entries..."
          className="input pl-10"
        />
      </div>

      {search && (
        <div className="font-mono text-[11px] text-ink-muted mb-3">
          // {search.total} results · backend: {search.backend}
          {search.backend === "postgres" && <span className="text-warn"> (degraded — elasticsearch unavailable)</span>}
        </div>
      )}

      {searchError && (
        <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg mb-3">! {searchError}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48"><Spinner /></div>
      ) : loadError ? (
        <div className="text-down text-xs font-mono p-4 bg-down/10 border border-down/20 rounded-lg">
          ! {loadError}
          <button onClick={load} className="ml-3 underline hover:text-down/80">retry</button>
        </div>
      ) : displayed.length === 0 ? (
        <EmptyState
          icon={<NotebookPen className="w-8 h-8" />}
          title={search ? "// no_results" : "// journal_empty"}
          description={search ? `No entries match "${query}"` : "Write your first entry to start building a searchable trade journal."}
          action={!search && (
            <button onClick={() => setModalOpen(true)} className="btn-primary">
              <Plus className="w-4 h-4" /> new entry
            </button>
          )}
        />
      ) : (
        <div className="flex flex-col gap-3">
          {displayed.map((e) => {
            const hl = "highlight" in e ? e.highlight : null;
            const titleHtml  = hl?.title ? sanitizeHighlight(hl.title) : null;
            const bodyHtml   = hl?.body  ? sanitizeHighlight(hl.body)  : null;
            return (
              <Link key={e.id} href={`/journal/${e.id}`} className="card p-4 hover:border-line-strong transition-colors block">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      {e.ticker && <Pill tone="cyan">{e.ticker}</Pill>}
                      {e.ai_generated && (
                        <Pill tone="accent"><Sparkles className="w-2.5 h-2.5" /> ai</Pill>
                      )}
                      {e.tags?.slice(0, 3).map((t) => (
                        <Pill key={t} tone="neutral">{t}</Pill>
                      ))}
                    </div>

                    {titleHtml ? (
                      <h3 className="font-semibold text-base mb-1"
                          dangerouslySetInnerHTML={{ __html: titleHtml }} />
                    ) : (
                      <h3 className="font-semibold text-base mb-1">{e.title}</h3>
                    )}

                    {bodyHtml ? (
                      <p className="text-sm text-ink-dim line-clamp-2"
                         dangerouslySetInnerHTML={{ __html: bodyHtml }} />
                    ) : (
                      <p className="text-sm text-ink-dim line-clamp-2">{e.body.slice(0, 200)}</p>
                    )}
                  </div>
                  <div className="font-mono text-[11px] text-ink-faint flex-shrink-0">
                    {timeAgo(e.created_at ?? null)}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      <NewEntryModal open={modalOpen} onClose={() => setModalOpen(false)} onSaved={load} />
    </div>
  );
}

function NewEntryModal({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const [title, setTitle]   = useState("");
  const [body, setBody]     = useState("");
  const [ticker, setTicker] = useState("");
  const [tags, setTags]     = useState("");
  const [error, setError]   = useState("");
  const [busy, setBusy]     = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await journalApi.create({
        title, body, ticker,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setTitle(""); setBody(""); setTicker(""); setTags("");
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to save");
    } finally { setBusy(false); }
  };

  return (
    <Modal open={open} onClose={onClose} title="new entry" width="lg">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div>
          <label className="label">title</label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)}
            required placeholder="PLTR breakout setup" className="input" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">ticker (optional)</label>
            <input type="text" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="PLTR" className="input font-mono" />
          </div>
          <div>
            <label className="label">tags (comma separated)</label>
            <input type="text" value={tags} onChange={(e) => setTags(e.target.value)}
              placeholder="breakout, earnings" className="input" />
          </div>
        </div>

        <div>
          <label className="label">body (markdown supported)</label>
          <textarea value={body} onChange={(e) => setBody(e.target.value)}
            required rows={10} placeholder="Your notes..." className="input resize-none font-sans leading-relaxed" />
        </div>

        {error && <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg">! {error}</div>}

        <div className="flex gap-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1">cancel</button>
          <button type="submit" disabled={busy} className="btn-primary flex-1">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {busy ? "saving" : "save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
