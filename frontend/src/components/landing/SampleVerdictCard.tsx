import { Eye, Gavel, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

const SIGNALS: { label: string; value: number }[] = [
  { label: "Source diversity", value: 0.78 },
  { label: "Freshness", value: 0.61 },
  { label: "Consensus", value: 0.74 },
  { label: "Evidence quality", value: 0.82 },
  { label: "Retrieval relevance", value: 0.7 },
];

const EVIDENCE = [
  {
    title: "Curiosity rover mineral analysis (NASA JPL)",
    snippet: "Clay minerals in Gale Crater indicate a long-lived lake environment with near-neutral pH - chemically suitable for microbial life, if any existed.",
    reliability: 0.91,
  },
  {
    title: "Ancient Martian groundwater duration study, Nature Astronomy (2023)",
    snippet: "Groundwater activity may have persisted far longer than surface lakes, extending the window of potential habitability by hundreds of millions of years.",
    reliability: 0.84,
  },
];

function reliabilityVariant(value: number): "success" | "warning" {
  return value >= 0.7 ? "success" : "warning";
}

/** A hand-composed, clearly-labeled example of what a research verdict
 * actually looks like - not a live query, so nobody mistakes it for a real
 * run, but built from the same visual components the product itself uses. */
export function SampleVerdictCard() {
  return (
    <div className="glass shadow-glow relative flex flex-col gap-5 overflow-hidden rounded-2xl border border-primary/25 p-6">
      <div className="bg-gradient-radial absolute -right-16 -top-16 h-56 w-56 from-primary/15 via-transparent to-transparent" />
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-2">
        <Badge variant="outline" className="gap-1.5 text-muted-foreground">
          <Eye className="h-3 w-3" /> Illustrative example, not a live query
        </Badge>
        <span className="text-xs text-muted-foreground">9-stage pipeline · 4 agents involved</span>
      </div>

      <p className="relative z-10 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">Question:</span> &ldquo;Did water on Mars ever
        support microbial life?&rdquo;
      </p>

      <div className="relative z-10 flex items-center gap-2.5">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-gold text-white">
          <Gavel className="h-4 w-4" />
        </span>
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Verdict
        </span>
      </div>
      <p className="relative z-10 -mt-3 font-display text-lg font-medium leading-snug sm:text-xl">
        Likely, but not yet confirmed - the evidence is suggestive, not conclusive.
      </p>

      <div className="relative z-10 flex flex-col gap-2 rounded-lg border border-border/60 bg-card/40 p-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl font-semibold">72%</span>
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

      <div className="relative z-10 flex flex-col gap-3">
        {EVIDENCE.map((item) => (
          <div key={item.title} className="flex gap-3 rounded-lg border border-border/60 bg-card/40 p-3.5">
            <div className="flex min-w-0 flex-1 flex-col gap-1.5">
              <div className="flex items-start justify-between gap-3">
                <p className="text-xs font-medium leading-snug">{item.title}</p>
                <Badge variant={reliabilityVariant(item.reliability)} className="shrink-0 text-[10px]">
                  {Math.round(item.reliability * 100)}% reliable
                </Badge>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">{item.snippet}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="relative z-10 flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 p-3.5">
        <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
        <p className="text-xs leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground">Devil&apos;s Advocate: </span>
          Ancient liquid water doesn&apos;t guarantee habitability - temperature and chemistry may
          still have been hostile even while water was present.
        </p>
      </div>
    </div>
  );
}
