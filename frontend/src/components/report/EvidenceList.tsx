import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { EvidenceItem } from "@/types";

function reliabilityVariant(reliability: number): "success" | "warning" | "destructive" {
  if (reliability >= 0.7) return "success";
  if (reliability >= 0.4) return "warning";
  return "destructive";
}

export function EvidenceList({ evidence }: { evidence: EvidenceItem[] }) {
  if (evidence.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          No evidence was retrieved for this query.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {evidence.map((item, i) => (
        <Card key={i} className="transition-colors hover:border-primary/30">
          <CardContent className="flex gap-3 pt-5">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-[11px] font-semibold text-muted-foreground">
              {i + 1}
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <div className="flex items-start justify-between gap-3">
                {item.claim && <p className="text-sm font-medium leading-snug">{item.claim}</p>}
                <Badge variant={reliabilityVariant(item.reliability)} className="shrink-0">
                  {Math.round(item.reliability * 100)}% reliable
                </Badge>
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">{item.snippet}</p>
              {item.source_url && (
                <a
                  href={item.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex w-fit items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:text-primary"
                >
                  <ExternalLink className="h-3 w-3" />
                  {item.source_title ?? item.source_url}
                </a>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
