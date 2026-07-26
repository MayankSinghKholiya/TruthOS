"use client";

import { Check, Copy, KeyRound, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiKeysApi } from "@/lib/api";
import type { ApiKeyCreated, ApiKeyRead } from "@/types";

/** Lets a human mint/revoke the X-API-Key credentials that let another
 * agent file disputes programmatically (POST /disputes/agent) as one of
 * their wallets, instead of going through this browser session. */
export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKeyRead[]>([]);
  const [walletId, setWalletId] = useState("");
  const [label, setLabel] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [justCreated, setJustCreated] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);

  function loadKeys() {
    apiKeysApi
      .list()
      .then(setKeys)
      .catch(() => setKeys([]));
  }

  useEffect(loadKeys, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!walletId.trim()) return;
    setIsCreating(true);
    try {
      const created = await apiKeysApi.create({ wallet_id: walletId.trim(), label: label.trim() || null });
      setJustCreated(created);
      setWalletId("");
      setLabel("");
      loadKeys();
    } finally {
      setIsCreating(false);
    }
  }

  async function handleRevoke(keyId: string) {
    await apiKeysApi.revoke(keyId);
    loadKeys();
  }

  function handleCopy() {
    if (!justCreated) return;
    navigator.clipboard.writeText(justCreated.key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="font-display text-2xl font-medium tracking-tight">Agent API keys</h1>
          <p className="text-sm text-muted-foreground">
            Lets another agent file disputes as one of your wallets directly (POST /disputes/agent),
            without going through this browser session - the A2A path into TruthOS Court.
          </p>
        </div>

        {justCreated && (
          <Card className="border-gold/40 shadow-glow">
            <CardHeader>
              <CardTitle className="text-sm">Your new key - copy it now</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <p className="text-xs text-muted-foreground">
                This is the only time the full key is shown. If you lose it, revoke it and create a new one.
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 truncate rounded-md bg-muted px-3 py-2 text-xs">
                  {justCreated.key}
                </code>
                <Button type="button" variant="outline" size="icon" onClick={handleCopy} aria-label="Copy key">
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Create a new key</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <div className="flex flex-1 flex-col gap-1.5">
                <Label htmlFor="wallet-id">Wallet ID</Label>
                <Input
                  id="wallet-id"
                  placeholder="0x... (the wallet this key can file disputes as)"
                  value={walletId}
                  onChange={(e) => setWalletId(e.target.value)}
                />
              </div>
              <div className="flex flex-1 flex-col gap-1.5">
                <Label htmlFor="label">Label (optional)</Label>
                <Input
                  id="label"
                  placeholder="e.g. production agent"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                />
              </div>
              <Button type="submit" disabled={isCreating || !walletId.trim()}>
                <KeyRound className="h-4 w-4" /> Generate key
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-muted-foreground">Existing keys</h2>
          {keys.length === 0 && <p className="text-sm text-muted-foreground">No API keys yet.</p>}
          {keys.map((key) => (
            <Card key={key.id}>
              <CardContent className="flex items-center justify-between gap-3 pt-5">
                <div className="flex min-w-0 flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <code className="text-xs text-muted-foreground">{key.key_prefix}...</code>
                    {key.revoked_at ? (
                      <Badge variant="destructive">Revoked</Badge>
                    ) : (
                      <Badge variant="success">Active</Badge>
                    )}
                  </div>
                  <p className="truncate font-mono text-xs text-muted-foreground">{key.wallet_id}</p>
                  {key.label && <p className="text-xs text-muted-foreground">{key.label}</p>}
                </div>
                {!key.revoked_at && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRevoke(key.id)}
                    aria-label="Revoke key"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </main>
  );
}
