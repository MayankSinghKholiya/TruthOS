"use client";

import { AlertTriangle, Loader2, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { courtApi } from "@/lib/api";
import type { Reputation } from "@/types";

/** Live red-flag check shown right where a respondent's wallet address is
 * typed - debounced so it doesn't fire on every keystroke, and silent until
 * there's enough of an address to look up. */
export function RespondentRiskCheck({ walletId }: { walletId: string }) {
  const [reputation, setReputation] = useState<Reputation | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const trimmed = walletId.trim();

  useEffect(() => {
    if (trimmed.length < 4) {
      setReputation(null);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    const timeout = setTimeout(() => {
      courtApi
        .getReputation(trimmed)
        .then(setReputation)
        .catch(() => setReputation(null))
        .finally(() => setIsLoading(false));
    }, 500);
    return () => clearTimeout(timeout);
  }, [trimmed]);

  if (trimmed.length < 4) return null;

  if (isLoading) {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" /> Checking reputation...
      </p>
    );
  }

  if (!reputation) return null;

  if (reputation.disputes_total === 0) {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <ShieldCheck className="h-3 w-3" /> No prior dispute history found for this wallet.
      </p>
    );
  }

  if (reputation.disputes_at_fault > 0) {
    return (
      <p className="flex items-center gap-1.5 text-xs font-medium text-destructive">
        <AlertTriangle className="h-3 w-3 shrink-0" />
        🚩 Found at fault in {reputation.disputes_at_fault} of {reputation.disputes_total} past
        dispute{reputation.disputes_total === 1 ? "" : "s"} - standing: {reputation.standing}.{" "}
        <Link href={`/court/reputation/${encodeURIComponent(trimmed)}`} className="underline" target="_blank">
          View history
        </Link>
      </p>
    );
  }

  return (
    <p className="flex items-center gap-1.5 text-xs text-success">
      <ShieldCheck className="h-3 w-3" /> Clean record across {reputation.disputes_total} past
      dispute{reputation.disputes_total === 1 ? "" : "s"}.
    </p>
  );
}
