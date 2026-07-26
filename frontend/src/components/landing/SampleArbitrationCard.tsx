import { Eye, Gavel } from "lucide-react";

import { ChainVerificationBadge } from "@/components/court/ChainVerificationBadge";
import { FaultSplitBar } from "@/components/court/FaultSplitBar";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

const SIGNALS: { label: string; value: number }[] = [
  { label: "Evidence completeness", value: 0.5 },
  { label: "Evidence decisiveness", value: 1.0 },
  { label: "Narrative consensus", value: 0.05 },
  { label: "Chain evidence integrity", value: 0.0 },
];

/** Same rule as SampleVerdictCard: clearly marked as illustrative, but
 * modeled closely on a real arbitration run against a fabricated
 * transaction reference - this is genuinely the kind of verdict the
 * on-chain check produces, not an invented best-case scenario. */
export function SampleArbitrationCard() {
  return (
    <div className="glass relative overflow-hidden rounded-2xl border border-gold/30 p-6 shadow-[0_0_0_1px_hsl(var(--gold)/0.12),0_8px_30px_-10px_hsl(var(--gold)/0.4)]">
      <div className="bg-gradient-radial absolute -right-16 -top-16 h-56 w-56 from-gold/20 via-transparent to-transparent" />
      <div className="relative z-10 flex flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Badge variant="outline" className="gap-1.5 text-muted-foreground">
            <Eye className="h-3 w-3" /> Illustrative example, not a live dispute
          </Badge>
          <span className="text-xs text-muted-foreground">250 USDC escrow · Base</span>
        </div>

        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Dispute:</span> claimant says the 250 USDC
          escrow payment was sent; respondent says nothing arrived, and delivery was conditioned on
          payment confirming first.
        </p>

        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-gold to-primary text-white">
            <Gavel className="h-4 w-4" />
          </span>
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Verdict
          </span>
        </div>
        <p className="-mt-3 font-display text-lg font-medium leading-snug sm:text-xl">
          Claimant at fault - the cited payment transaction does not exist on-chain.
        </p>

        <FaultSplitBar claimantFaultPercentage={100} respondentFaultPercentage={0} />

        <div className="flex items-center gap-2 rounded-lg bg-card/40 px-3 py-2 text-sm">
          <span className="text-muted-foreground">Refund recommendation:</span>
          <span className="font-semibold">0% of escrow</span>
        </div>

        <div className="flex items-center justify-between rounded-lg border border-border/60 bg-card/40 p-3.5">
          <div>
            <p className="text-xs font-medium">Claimant&apos;s evidence: tx reference on Base</p>
            <p className="text-[11px] text-muted-foreground">Checked directly against the chain, not taken on their word.</p>
          </div>
          <ChainVerificationBadge status="not_found" />
        </div>

        <div className="flex flex-col gap-2 rounded-lg border border-border/60 bg-card/40 p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-semibold">33%</span>
            <span className="text-xs text-muted-foreground">Confidence DNA - overall</span>
          </div>
          <div className="grid gap-2.5 sm:grid-cols-2">
            {SIGNALS.map((signal) => (
              <div key={signal.label} className="flex flex-col gap-1">
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>{signal.label}</span>
                  <span>{Math.round(signal.value * 100)}%</span>
                </div>
                <Progress value={signal.value * 100} className="h-1.5" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
