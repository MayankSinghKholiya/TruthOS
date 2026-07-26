import { FileText } from "lucide-react";

import { ChainVerificationBadge } from "@/components/court/ChainVerificationBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { DisputeEvidenceRead } from "@/types";

/** The raw evidence rows a dispute was filed with, shown as submitted - not
 * filtered through any agent's summary, so a fabricated or contradicted
 * tx-reference is visible immediately, before arbitration ever runs. */
export function SubmittedEvidenceList({ evidence }: { evidence: DisputeEvidenceRead[] }) {
  if (evidence.length === 0) {
    return <p className="text-sm text-muted-foreground">No evidence was submitted with this dispute.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {evidence.map((item) => (
        <Card key={item.id}>
          <CardContent className="flex items-start gap-3 pt-5">
            <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="capitalize">
                  {item.submitted_by}
                </Badge>
                <span className="text-xs text-muted-foreground">{item.evidence_type}</span>
                {item.chain && (
                  <span className="text-xs uppercase text-muted-foreground">on {item.chain}</span>
                )}
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{item.content}</p>
              {item.verification_status && (
                <ChainVerificationBadge
                  status={item.verification_status}
                  explorerUrl={
                    (item.verification_details?.explorer_url as string | undefined) ?? undefined
                  }
                />
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
