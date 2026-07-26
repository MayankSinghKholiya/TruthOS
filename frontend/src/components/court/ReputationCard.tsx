import { ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { Reputation } from "@/types";

const STANDING_VARIANT: Record<Reputation["standing"], "success" | "secondary" | "destructive"> = {
  Trusted: "success",
  Neutral: "secondary",
  Flagged: "destructive",
};

function scoreColor(score: number): string {
  if (score >= 80) return "bg-success";
  if (score >= 50) return "bg-warning";
  return "bg-destructive";
}

export function ReputationCard({ reputation }: { reputation: Reputation }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <CardTitle className="font-mono text-sm">{reputation.wallet_id}</CardTitle>
        </div>
        <Badge variant={STANDING_VARIANT[reputation.standing]}>{reputation.standing}</Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-center gap-4">
          <span className="text-3xl font-semibold">{Math.round(reputation.trust_score)}</span>
          <Progress
            value={reputation.trust_score}
            className="h-3 flex-1"
            indicatorClassName={scoreColor(reputation.trust_score)}
          />
        </div>
        <div className="grid grid-cols-3 gap-3 text-center text-sm">
          <div>
            <p className="text-lg font-semibold">{reputation.disputes_total}</p>
            <p className="text-xs text-muted-foreground">Disputes</p>
          </div>
          <div>
            <p className="text-lg font-semibold">{reputation.disputes_at_fault}</p>
            <p className="text-xs text-muted-foreground">At fault</p>
          </div>
          <div>
            <p className="text-lg font-semibold">{reputation.completed_tasks}</p>
            <p className="text-xs text-muted-foreground">Completed</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
