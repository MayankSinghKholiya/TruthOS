"use client";

import { Bell, Check, Copy, Send, ShieldAlert, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { telegramApi } from "@/lib/api";
import type { TelegramLinkStart, TelegramLinkStatus, WalletWatchRead } from "@/types";

/** Lets a human link a Telegram chat to their TruthOS account and choose
 * which wallets to watch - the other half of app.services.telegram_notify:
 * a dispute filed against a watched wallet, or a just-resolved verdict that
 * leaves a counterparty Flagged, gets pushed here instead of requiring a
 * manual reputation check. */
export default function TelegramSettingsPage() {
  const [status, setStatus] = useState<TelegramLinkStatus | null>(null);
  const [linkStart, setLinkStart] = useState<TelegramLinkStart | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [copied, setCopied] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [watches, setWatches] = useState<WalletWatchRead[]>([]);
  const [walletId, setWalletId] = useState("");
  const [label, setLabel] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  function loadStatus() {
    telegramApi
      .linkStatus()
      .then(setStatus)
      .catch(() => setStatus({ linked: false, telegram_username: null, linked_at: null }));
  }

  function loadWatches() {
    telegramApi
      .listWatches()
      .then(setWatches)
      .catch(() => setWatches([]));
  }

  useEffect(() => {
    loadStatus();
    loadWatches();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function handleStartLink() {
    setIsStarting(true);
    try {
      const started = await telegramApi.startLink();
      setLinkStart(started);
      // Poll every 3s until the background long-poll handshake completes on
      // the backend and marks this account linked.
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        const current = await telegramApi.linkStatus();
        setStatus(current);
        if (current.linked) {
          setLinkStart(null);
          if (pollRef.current) clearInterval(pollRef.current);
        }
      }, 3000);
    } finally {
      setIsStarting(false);
    }
  }

  async function handleUnlink() {
    await telegramApi.unlink();
    setStatus({ linked: false, telegram_username: null, linked_at: null });
  }

  async function handleAddWatch(e: React.FormEvent) {
    e.preventDefault();
    if (!walletId.trim()) return;
    setIsAdding(true);
    try {
      await telegramApi.createWatch({ wallet_id: walletId.trim(), label: label.trim() || null });
      setWalletId("");
      setLabel("");
      loadWatches();
    } finally {
      setIsAdding(false);
    }
  }

  async function handleRemoveWatch(id: string) {
    await telegramApi.deleteWatch(id);
    loadWatches();
  }

  function handleCopyLink() {
    if (!linkStart) return;
    const url = linkStart.bot_username
      ? `https://t.me/${linkStart.bot_username}?start=${linkStart.code}`
      : linkStart.code;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="font-display text-2xl font-medium tracking-tight">Telegram alerts</h1>
          <p className="text-sm text-muted-foreground">
            Get notified the moment a dispute is filed against a wallet you&apos;re watching, or when a
            wallet you dealt with just got Flagged - with the dispute ID, timestamp, and any on-chain
            reference, straight to Telegram.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Telegram connection</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {status?.linked ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="success" className="gap-1.5">
                    <Check className="h-3 w-3" /> Connected
                  </Badge>
                  {status.telegram_username && (
                    <span className="text-sm text-muted-foreground">@{status.telegram_username}</span>
                  )}
                </div>
                <Button variant="outline" size="sm" onClick={handleUnlink}>
                  Disconnect
                </Button>
              </div>
            ) : linkStart ? (
              <div className="flex flex-col gap-3">
                <p className="text-sm text-muted-foreground">
                  Open Telegram and send this code to the bot, or tap the link below:
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 rounded-md bg-muted px-3 py-2 text-center text-lg font-semibold tracking-widest">
                    {linkStart.code}
                  </code>
                  <Button type="button" variant="outline" size="icon" onClick={handleCopyLink} aria-label="Copy">
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                {linkStart.bot_username && (
                  <Button asChild>
                    <a
                      href={`https://t.me/${linkStart.bot_username}?start=${linkStart.code}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <Send className="h-4 w-4" /> Open @{linkStart.bot_username}
                    </a>
                  </Button>
                )}
                <p className="text-xs text-muted-foreground">
                  Waiting for confirmation - this updates automatically once linked. Code expires in{" "}
                  {Math.round(linkStart.expires_in_seconds / 60)} minutes.
                </p>
              </div>
            ) : (
              <Button onClick={handleStartLink} disabled={isStarting}>
                <Bell className="h-4 w-4" /> Connect Telegram
              </Button>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Watch a wallet</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddWatch} className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <div className="flex flex-1 flex-col gap-1.5">
                <Label htmlFor="wallet-id">Wallet ID</Label>
                <Input
                  id="wallet-id"
                  placeholder="0x... (your own agent's wallet, or one you deal with)"
                  value={walletId}
                  onChange={(e) => setWalletId(e.target.value)}
                />
              </div>
              <div className="flex flex-1 flex-col gap-1.5">
                <Label htmlFor="watch-label">Label (optional)</Label>
                <Input
                  id="watch-label"
                  placeholder="e.g. my trading agent"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                />
              </div>
              <Button type="submit" disabled={isAdding || !walletId.trim()}>
                <ShieldAlert className="h-4 w-4" /> Watch
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-muted-foreground">Watched wallets</h2>
          {watches.length === 0 && <p className="text-sm text-muted-foreground">Not watching any wallets yet.</p>}
          {watches.map((watch) => (
            <Card key={watch.id}>
              <CardContent className="flex items-center justify-between gap-3 pt-5">
                <div className="flex min-w-0 flex-col gap-1">
                  <code className="truncate text-xs">{watch.wallet_id}</code>
                  {watch.label && <p className="text-xs text-muted-foreground">{watch.label}</p>}
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveWatch(watch.id)}
                  aria-label="Stop watching"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </main>
  );
}
