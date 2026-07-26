import { ShieldAlert } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { CounterArgument } from "@/types";

export function CounterArguments({ counterArguments }: { counterArguments: CounterArgument[] }) {
  if (counterArguments.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          No significant counter-arguments were raised.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {counterArguments.map((arg, i) => (
        <div
          key={i}
          className="relative flex gap-3 overflow-hidden rounded-xl border border-warning/25 bg-warning/[0.04] p-4"
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-warning/15 text-warning">
            <ShieldAlert className="h-4 w-4" />
          </span>
          <div className="flex min-w-0 flex-1 flex-col gap-2">
            <p className="text-sm leading-snug">{arg.argument}</p>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium capitalize text-muted-foreground">
                {arg.raised_by}
              </span>
              <Progress value={arg.strength * 100} className="h-1 w-20" indicatorClassName="bg-warning" />
              <span className="text-[11px] text-muted-foreground">{Math.round(arg.strength * 100)}%</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
