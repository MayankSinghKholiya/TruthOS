import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { ConfidenceBreakdown } from "@/types";

const SIGNAL_LABELS: Record<keyof Omit<ConfidenceBreakdown, "overall">, string> = {
  source_diversity: "Source diversity",
  freshness: "Freshness",
  consensus: "Consensus",
  evidence_quality: "Evidence quality",
  retrieval_confidence: "Retrieval confidence",
};

function scoreColor(value: number): string {
  if (value >= 0.7) return "bg-success";
  if (value >= 0.4) return "bg-warning";
  return "bg-destructive";
}

export function ConfidenceDashboard({ confidence }: { confidence: ConfidenceBreakdown }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Confidence DNA</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-center gap-4">
          <span className="text-3xl font-semibold">{Math.round(confidence.overall * 100)}%</span>
          <Progress
            value={confidence.overall * 100}
            className="h-3 flex-1"
            indicatorClassName={scoreColor(confidence.overall)}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {(Object.keys(SIGNAL_LABELS) as (keyof typeof SIGNAL_LABELS)[]).map((key) => (
            <div key={key} className="flex flex-col gap-1">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{SIGNAL_LABELS[key]}</span>
                <span>{Math.round(confidence[key] * 100)}%</span>
              </div>
              <Progress
                value={confidence[key] * 100}
                className="h-1.5"
                indicatorClassName={scoreColor(confidence[key])}
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
