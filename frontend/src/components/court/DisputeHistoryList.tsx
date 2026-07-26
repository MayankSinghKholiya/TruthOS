import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { DisputeHistoryEntry } from "@/types";

const STATUS_VARIANT: Record<string, "success" | "secondary" | "destructive"> = {
  resolved: "success",
  open: "secondary",
  failed: "destructive",
};

export function DisputeHistoryList({ history }: { history: DisputeHistoryEntry[] }) {
  if (history.length === 0) {
    return <p className="text-sm text-muted-foreground">No past disputes found for this wallet.</p>;
  }

  return (
    <div className="flex flex-col gap-2.5">
      {history.map((entry) => (
        <Card key={entry.dispute_id}>
          <CardContent className="flex flex-col gap-1.5 py-4">
            <div className="flex items-center justify-between gap-2">
              <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium capitalize text-muted-foreground">
                as {entry.role}
              </span>
              <Badge variant={STATUS_VARIANT[entry.status] ?? "secondary"} className="capitalize">
                {entry.status}
              </Badge>
            </div>
            <p className="text-sm leading-snug">{entry.task_description}</p>
            {entry.verdict && (
              <p className="text-xs text-muted-foreground">
                Verdict: {entry.verdict}
                {entry.fault_percentage != null && (
                  <span
                    className={
                      entry.fault_percentage > 50
                        ? "ml-1 font-medium text-destructive"
                        : "ml-1 font-medium text-success"
                    }
                  >
                    ({entry.fault_percentage}% at fault)
                  </span>
                )}
              </p>
            )}
            <p className="text-[11px] text-muted-foreground/70">
              {new Date(entry.created_at).toLocaleDateString(undefined, {
                year: "numeric",
                month: "short",
                day: "numeric",
              })}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
