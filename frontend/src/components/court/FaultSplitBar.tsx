interface FaultSplitBarProps {
  claimantFaultPercentage: number;
  respondentFaultPercentage: number;
  claimantLabel?: string;
  respondentLabel?: string;
}

export function FaultSplitBar({
  claimantFaultPercentage,
  respondentFaultPercentage,
  claimantLabel = "Claimant",
  respondentLabel = "Respondent",
}: FaultSplitBarProps) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-4 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className="h-full bg-warning transition-all duration-700"
          style={{ width: `${claimantFaultPercentage}%` }}
          title={`${claimantLabel} fault: ${claimantFaultPercentage}%`}
        />
        <div
          className="h-full bg-destructive transition-all duration-700"
          style={{ width: `${respondentFaultPercentage}%` }}
          title={`${respondentLabel} fault: ${respondentFaultPercentage}%`}
        />
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>
          {claimantLabel}: <span className="font-medium text-foreground">{claimantFaultPercentage}%</span> at fault
        </span>
        <span>
          {respondentLabel}: <span className="font-medium text-foreground">{respondentFaultPercentage}%</span> at fault
        </span>
      </div>
    </div>
  );
}
