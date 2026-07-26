import { Gavel } from "lucide-react";

export function VerdictCard({ verdict }: { verdict: string }) {
  return (
    <div className="glass shadow-glow relative overflow-hidden rounded-xl border border-primary/25 p-5">
      <div className="bg-gradient-radial absolute -right-10 -top-10 h-40 w-40 from-primary/20 via-transparent to-transparent" />
      <div className="relative z-10 flex items-center gap-2.5">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-gold text-white">
          <Gavel className="h-4 w-4" />
        </span>
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Verdict
        </span>
      </div>
      <p className="relative z-10 mt-3 font-display text-xl font-medium leading-snug">{verdict}</p>
    </div>
  );
}
