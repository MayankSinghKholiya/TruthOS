"use client";

import { ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ReputationSearchPage() {
  const router = useRouter();
  const [walletId, setWalletId] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = walletId.trim();
    if (!trimmed) return;
    router.push(`/court/reputation/${encodeURIComponent(trimmed)}`);
  }

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-lg flex-col gap-6 px-6 py-16">
        <div className="flex flex-col items-center gap-3 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 to-gold/20 text-primary">
            <ShieldCheck className="h-6 w-6" />
          </span>
          <h1 className="font-display text-3xl font-medium tracking-tight">
            Check an agent&apos;s trust score
          </h1>
          <p className="text-sm text-muted-foreground">
            Look up any wallet&apos;s dispute history before you transact with it - built from every
            verdict TruthOS Court has issued.
          </p>
        </div>
        <Card className="shadow-glow">
          <CardHeader>
            <CardTitle className="text-sm">Wallet ID</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="wallet" className="sr-only">
                  Wallet ID
                </Label>
                <Input
                  id="wallet"
                  placeholder="0x..."
                  value={walletId}
                  onChange={(e) => setWalletId(e.target.value)}
                  autoFocus
                />
              </div>
              <Button type="submit" size="lg" disabled={!walletId.trim()}>
                Look up trust score
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
