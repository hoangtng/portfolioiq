"use client";

import { useState, useEffect } from "react";
import { Save, Loader2, Check, LogOut, Send } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { PageHeader, Pill } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { auth, ApiError } from "@/lib/api";

export default function SettingsPage() {
  return (<AppShell><Settings /></AppShell>);
}

function Settings() {
  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-[800px] mx-auto">
      <PageHeader title="settings" />
      <div className="flex flex-col gap-6">
        <ProfileSection />
        <PasswordSection />
        <TelegramSection />
        <AccountSection />
      </div>
    </div>
  );
}

// ─── Profile ────────────────────────────────────────────────

function ProfileSection() {
  const { user, refreshMe } = useAuth();
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName,  setLastName]  = useState(user?.last_name ?? "");
  const [bio,       setBio]       = useState(user?.bio ?? "");
  const [avatar,    setAvatar]    = useState(user?.avatar_url ?? "");
  const [busy, setBusy]   = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user) {
      setFirstName(user.first_name);
      setLastName(user.last_name);
      setBio(user.bio);
      setAvatar(user.avatar_url);
    }
  }, [user]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await auth.updateMe({ first_name: firstName, last_name: lastName, bio, avatar_url: avatar });
      await refreshMe();
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to save");
    } finally { setBusy(false); }
  };

  return (
    <section className="card p-5 sm:p-6">
      <h2 className="section-title mb-4">profile</h2>

      <div className="flex items-center gap-4 mb-6 pb-6 border-b border-line">
        {avatar ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={avatar} alt="Avatar" className="w-16 h-16 rounded-full border border-line-strong" />
        ) : (
          <div className="w-16 h-16 rounded-full bg-bg-card border border-line-strong flex items-center justify-center font-mono font-bold text-xl">
            {(user?.first_name?.[0] || user?.email?.[0] || "?").toUpperCase()}
          </div>
        )}
        <div>
          <div className="font-mono font-semibold">{user?.display_name}</div>
          <div className="font-mono text-xs text-ink-muted">{user?.email}</div>
        </div>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="label">first name</label>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} className="input" />
          </div>
          <div>
            <label className="label">last name</label>
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} className="input" />
          </div>
        </div>

        <div>
          <label className="label">avatar url</label>
          <input value={avatar} onChange={(e) => setAvatar(e.target.value)}
            placeholder="https://..." className="input font-mono text-xs" />
        </div>

        <div>
          <label className="label">bio</label>
          <textarea value={bio} onChange={(e) => setBio(e.target.value)}
            rows={3} placeholder="A short bio about yourself" className="input resize-none" />
        </div>

        {error && <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg">! {error}</div>}

        <div className="flex items-center gap-3">
          <button type="submit" disabled={busy} className="btn-primary">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            save
          </button>
          {saved && (
            <span className="font-mono text-xs text-accent flex items-center gap-1">
              <Check className="w-3 h-3" /> saved
            </span>
          )}
        </div>
      </form>
    </section>
  );
}

// ─── Password ───────────────────────────────────────────────

function PasswordSection() {
  const [current, setCurrent] = useState("");
  const [newPw, setNewPw]     = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy]   = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await auth.changePassword({
        current_password: current,
        new_password:     newPw,
        confirm_password: confirm,
      });
      setCurrent(""); setNewPw(""); setConfirm("");
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof ApiError
        ? (typeof e.data === "object" && e.data
          ? JSON.stringify(e.data).replace(/[{}"\[\]]/g, "").replace(/,/g, " · ")
          : e.message)
        : "Failed to change password");
    } finally { setBusy(false); }
  };

  return (
    <section className="card p-5 sm:p-6">
      <h2 className="section-title mb-4">change password</h2>

      <form onSubmit={submit} className="flex flex-col gap-4">
        <div>
          <label className="label">current password</label>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)}
            required autoComplete="current-password" className="input" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="label">new password</label>
            <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)}
              required minLength={8} autoComplete="new-password" className="input" />
          </div>
          <div>
            <label className="label">confirm</label>
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
              required autoComplete="new-password" className="input" />
          </div>
        </div>

        {error && <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg">{error}</div>}

        <div className="flex items-center gap-3">
          <button type="submit" disabled={busy} className="btn-primary">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            update
          </button>
          {saved && <span className="font-mono text-xs text-accent flex items-center gap-1"><Check className="w-3 h-3" /> updated</span>}
        </div>
      </form>
    </section>
  );
}

// ─── Telegram ───────────────────────────────────────────────

function TelegramSection() {
  const { user, refreshMe } = useAuth();
  const [chatId, setChatId] = useState(user?.telegram_chat_id ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => { setChatId(user?.telegram_chat_id ?? ""); }, [user]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (chatId && !/^-?\d+$/.test(chatId)) {
      setError("chat_id must be a number (e.g. 123456789)");
      return;
    }
    setError(""); setBusy(true);
    try {
      await auth.updateMe({ telegram_chat_id: chatId });
      await refreshMe();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to link");
    } finally { setBusy(false); }
  };

  return (
    <section className="card p-5 sm:p-6">
      <h2 className="section-title mb-1 flex items-center gap-2">
        <Send className="w-3.5 h-3.5" /> telegram integration
      </h2>
      <p className="font-mono text-xs text-ink-muted mb-4">
        Get price alerts and analyze from telegram
      </p>

      <div className="bg-bg-deepest border border-line rounded-lg p-4 mb-4">
        <ol className="font-mono text-xs text-ink-dim flex flex-col gap-2 list-decimal list-inside">
          <li>open telegram, find <span className="text-accent">@PortfolioIQ_bot</span></li>
          <li>send <span className="text-accent">/start</span> to it</li>
          <li>the bot replies with your <span className="text-accent">chat_id</span></li>
          <li>paste it below and save</li>
        </ol>
      </div>

      <form onSubmit={submit} className="flex gap-2 items-end flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <label className="label">chat_id</label>
          <input value={chatId} onChange={(e) => setChatId(e.target.value)}
            placeholder="123456789" className="input font-mono" />
        </div>
        <button type="submit" disabled={busy} className="btn-primary">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          link
        </button>
        {user?.telegram_chat_id && (
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setError(""); setBusy(true);
              try {
                await auth.updateMe({ telegram_chat_id: "" });
                await refreshMe();
                setChatId("");
              } catch (e) {
                setError(e instanceof ApiError ? e.message : "Failed to unlink");
              } finally { setBusy(false); }
            }}
            className="btn-secondary"
          >
            unlink
          </button>
        )}
      </form>

      {user?.telegram_chat_id && (
        <div className="mt-3">
          <Pill tone="accent"><Check className="w-2.5 h-2.5" /> linked to {user.telegram_chat_id}</Pill>
        </div>
      )}

      {error && <div className="text-down text-xs font-mono p-3 bg-down/10 border border-down/20 rounded-lg mt-3">! {error}</div>}
      {saved && <div className="text-accent text-xs font-mono mt-3 flex items-center gap-1"><Check className="w-3 h-3" /> saved</div>}
    </section>
  );
}

// ─── Account ────────────────────────────────────────────────

function AccountSection() {
  const { logout } = useAuth();
  return (
    <section className="card p-5 sm:p-6">
      <h2 className="section-title mb-4">account</h2>
      <button onClick={logout} className="btn-secondary text-down hover:text-down border-down/20 hover:bg-down/10">
        <LogOut className="w-4 h-4" /> sign out
      </button>
    </section>
  );
}
