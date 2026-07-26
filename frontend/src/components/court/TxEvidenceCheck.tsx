"use client";

import { Loader2, Search } from "lucide-react";
import { useState } from "react";

import { ChainVerificationBadge } from "@/components/court/ChainVerificationBadge";
import { Button } from "@/components/ui/button";
import { courtApi } from "@/lib/api";
import type { ChainVerification } from "@/types";

/** On-demand (button-triggered, not debounced) on-chain preview for a
 * tx_reference evidence row being composed - a tx hash is usually pasted in
 * one go rather than typed character by character, so a manual check gives
 * cleaner control than firing a lookup on every keystroke. The dispute is
 * re-checked server-side at submission regardless; this is just an early
 * look so the filer isn't surprised by the result afterward. */
export function TxEvidenceCheck({
  chain,
  content,
  escrowAmount,
}: {
  chain: string;
  content: string;
  escrowAmount?: number | null;
}) {
  const [result, setResult] = useState<ChainVerification | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  async function handleCheck() {
    setIsChecking(true);
    setResult(null);
    try {
      const verification = await courtApi.verifyTx(chain, content, escrowAmount ?? undefined);
      setResult(verification);
    } catch {
      setResult(null);
    } finally {
      setIsChecking(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={isChecking || content.trim().length < 10}
        onClick={handleCheck}
      >
        {isChecking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
        Check on-chain
      </Button>
      {result && <ChainVerificationBadge status={result.status} explorerUrl={result.explorer_url} />}
    </div>
  );
}
