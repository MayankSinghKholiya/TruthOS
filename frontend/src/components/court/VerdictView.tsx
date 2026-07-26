import { Gavel, Link2, ShieldAlert } from "lucide-react";

import { FaultSplitBar } from "@/components/court/FaultSplitBar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Dispute, DisputeVerdict } from "@/types";

function scoreColor(value: number): string {
  if (value >= 0.7) return "bg-success";
  if (value >= 0.4) return "bg-warning";
  return "bg-destructive";
}

export function VerdictView({ dispute, verdict }: { dispute: Dispute; verdict: DisputeVerdict }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="glass relative overflow-hidden rounded-xl border border-gold/30 p-5 shadow-[0_0_0_1px_hsl(var(--gold)/0.12),0_8px_30px_-10px_hsl(var(--gold)/0.4)]">
        <div className="bg-gradient-radial absolute -right-10 -top-10 h-40 w-40 from-gold/25 via-transparent to-transparent" />
        <div className="relative z-10 flex flex-col gap-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-gold to-primary text-white">
              <Gavel className="h-4 w-4" />
            </span>
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Verdict
            </span>
          </div>
          <p className="font-display text-xl font-medium leading-snug">{verdict.verdict}</p>
          <FaultSplitBar
            claimantFaultPercentage={verdict.claimant_fault_percentage}
            respondentFaultPercentage={verdict.respondent_fault_percentage}
          />
          <div className="flex items-center gap-2 rounded-lg bg-background/60 px-3 py-2 text-sm">
            <span className="text-muted-foreground">Refund recommendation:</span>
            <span className="font-semibold">
              {verdict.refund_recommendation_percentage}%
              {dispute.escrow_amount != null && (
                <span className="ml-1 text-muted-foreground">
                  (~
                  {((dispute.escrow_amount * verdict.refund_recommendation_percentage) / 100).toFixed(2)}{" "}
                  of escrow)
                </span>
              )}
            </span>
          </div>
        </div>
      </div>

      <Tabs defaultValue="summary">
        <TabsList>
          <TabsTrigger value="summary">Executive Summary</TabsTrigger>
          <TabsTrigger value="confidence">Confidence</TabsTrigger>
          <TabsTrigger value="timeline">Evidence Timeline ({verdict.evidence_timeline.length})</TabsTrigger>
          <TabsTrigger value="counter">Counter-Arguments ({verdict.counter_arguments.length})</TabsTrigger>
          <TabsTrigger value="reasoning">Reasoning</TabsTrigger>
        </TabsList>

        <TabsContent value="summary">
          <Card>
            <CardHeader>
              <CardTitle>Executive Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed">{verdict.executive_summary}</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="confidence">
          <Card>
            <CardHeader>
              <CardTitle>Confidence DNA</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-center gap-4">
                <span className="text-3xl font-semibold">
                  {Math.round(verdict.confidence_breakdown.overall * 100)}%
                </span>
                <Progress
                  value={verdict.confidence_breakdown.overall * 100}
                  className="h-3 flex-1"
                  indicatorClassName={scoreColor(verdict.confidence_breakdown.overall)}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {(
                  [
                    ["Evidence completeness", verdict.confidence_breakdown.evidence_completeness],
                    ["Evidence decisiveness", verdict.confidence_breakdown.evidence_decisiveness],
                    ["Narrative consensus", verdict.confidence_breakdown.narrative_consensus],
                    ["Chain evidence integrity", verdict.confidence_breakdown.chain_evidence_integrity],
                  ] as [string, number][]
                ).map(([label, value]) => (
                  <div key={label} className="flex flex-col gap-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{label}</span>
                      <span>{Math.round(value * 100)}%</span>
                    </div>
                    <Progress value={value * 100} className="h-1.5" indicatorClassName={scoreColor(value)} />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="timeline">
          <div className="flex flex-col gap-3">
            {verdict.evidence_timeline.length === 0 && (
              <p className="text-sm text-muted-foreground">No evidence timeline available.</p>
            )}
            {verdict.evidence_timeline.map((entry, i) => (
              <Card key={i}>
                <CardContent className="flex items-start gap-3 pt-5">
                  <Link2 className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="capitalize">
                        {entry.submitted_by}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{entry.evidence_type}</span>
                    </div>
                    <p className="mt-1 text-sm">{entry.summary}</p>
                  </div>
                  <Progress value={entry.weight * 100} className="mt-1 h-1.5 w-16" />
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="counter">
          <div className="flex flex-col gap-3">
            {verdict.counter_arguments.length === 0 && (
              <p className="text-sm text-muted-foreground">No significant counter-arguments were raised.</p>
            )}
            {verdict.counter_arguments.map((arg, i) => (
              <div key={i} className="flex flex-col gap-2 rounded-lg border border-border p-4">
                <div className="flex items-start gap-2">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                  <p className="text-sm">{arg.argument}</p>
                </div>
                <div className="flex items-center gap-2 pl-6">
                  <span className="text-xs capitalize text-muted-foreground">{arg.raised_by}</span>
                  <Progress value={arg.strength * 100} className="h-1 w-24" />
                </div>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="reasoning">
          <Card>
            <CardHeader>
              <CardTitle>Arbitrator Reasoning</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{verdict.reasoning}</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
