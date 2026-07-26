import { AlertTriangle, ShieldCheck } from "lucide-react";

import type { Reputation } from "@/types";

export function RedFlagBanner({ reputation }: { reputation: Reputation }) {
  if (reputation.disputes_total === 0) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-muted/40 p-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
          <ShieldCheck className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-medium">No dispute history yet</p>
          <p className="text-xs text-muted-foreground">
            This wallet hasn&apos;t been party to any TruthOS Court dispute.
          </p>
        </div>
      </div>
    );
  }

  if (reputation.standing === "Flagged" || reputation.disputes_at_fault >= 2) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-destructive/40 bg-destructive/10 p-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-destructive/20 text-destructive">
          <AlertTriangle className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-semibold text-destructive">🚩 Red flag - proceed with caution</p>
          <p className="text-xs text-muted-foreground">
            Found at fault in {reputation.disputes_at_fault} of {reputation.disputes_total} past
            dispute{reputation.disputes_total === 1 ? "" : "s"}. Review the history below before
            transacting with this wallet.
          </p>
        </div>
      </div>
    );
  }

  if (reputation.disputes_at_fault > 0) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-warning/40 bg-warning/10 p-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-warning/20 text-warning">
          <AlertTriangle className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-semibold text-warning">Some history to review</p>
          <p className="text-xs text-muted-foreground">
            At fault in {reputation.disputes_at_fault} of {reputation.disputes_total} past dispute
            {reputation.disputes_total === 1 ? "" : "s"} - still generally in good standing.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 rounded-xl border border-success/40 bg-success/10 p-4">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-success/20 text-success">
        <ShieldCheck className="h-4 w-4" />
      </span>
      <div>
        <p className="text-sm font-semibold text-success">No red flags found</p>
        <p className="text-xs text-muted-foreground">
          Clean record across {reputation.disputes_total} past dispute
          {reputation.disputes_total === 1 ? "" : "s"}.
        </p>
      </div>
    </div>
  );
}
