"use client";

import { History } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DisputeHistoryList } from "@/components/court/DisputeHistoryList";
import { RedFlagBanner } from "@/components/court/RedFlagBanner";
import { ReputationCard } from "@/components/court/ReputationCard";
import { courtApi } from "@/lib/api";
import type { DisputeHistoryEntry, Reputation } from "@/types";

export default function ReputationDetailPage() {
  const params = useParams<{ walletId: string }>();
  const walletId = decodeURIComponent(params.walletId);
  const [reputation, setReputation] = useState<Reputation | null>(null);
  const [history, setHistory] = useState<DisputeHistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setReputation(null);
    setHistory([]);
    setError(null);
    Promise.all([courtApi.getReputation(walletId), courtApi.getReputationHistory(walletId)])
      .then(([rep, hist]) => {
        setReputation(rep);
        setHistory(hist);
      })
      .catch(() => setError("Could not load reputation for this wallet."));
  }, [walletId]);

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-lg flex-col gap-5 px-6 py-10">
        <h1 className="font-display text-2xl font-medium tracking-tight">Trust score</h1>
        {error && <p className="text-sm text-destructive">{error}</p>}

        {reputation ? (
          <>
            <RedFlagBanner reputation={reputation} />
            <ReputationCard reputation={reputation} />

            <div className="mt-2 flex flex-col gap-3">
              <h2 className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <History className="h-4 w-4" /> Dispute history
              </h2>
              <DisputeHistoryList history={history} />
            </div>
          </>
        ) : (
          !error && <p className="text-sm text-muted-foreground">Loading...</p>
        )}
      </div>
    </main>
  );
}
