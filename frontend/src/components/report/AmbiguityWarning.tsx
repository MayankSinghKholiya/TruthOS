import { AlertTriangle } from "lucide-react";

import type { EntityAmbiguity } from "@/types";

export function AmbiguityWarning({ ambiguity }: { ambiguity: EntityAmbiguity }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-warning/40 bg-warning/10 p-4">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
      <div>
        <p className="text-sm font-medium text-foreground">
          This query may be ambiguous - the answer below might not be about what you meant.
        </p>
        <p className="mt-1 text-sm text-muted-foreground">{ambiguity.explanation}</p>
      </div>
    </div>
  );
}
