import { AlertTriangle, Clock, ExternalLink, HelpCircle, ShieldCheck, WifiOff, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ChainVerificationStatus } from "@/types";

const STATUS_CONFIG: Record<
  ChainVerificationStatus,
  { label: string; variant: "success" | "warning" | "destructive" | "outline"; icon: typeof ShieldCheck }
> = {
  confirmed_match: { label: "Verified on-chain", variant: "success", icon: ShieldCheck },
  confirmed: { label: "Confirmed on-chain", variant: "success", icon: ShieldCheck },
  confirmed_mismatch: { label: "Amount mismatch on-chain", variant: "destructive", icon: AlertTriangle },
  failed_onchain: { label: "Transaction failed on-chain", variant: "destructive", icon: AlertTriangle },
  not_found: { label: "Not found on-chain", variant: "destructive", icon: XCircle },
  pending: { label: "Pending confirmation", variant: "warning", icon: Clock },
  invalid_format: { label: "No valid tx hash", variant: "outline", icon: HelpCircle },
  unsupported_chain: { label: "Unsupported chain", variant: "outline", icon: HelpCircle },
  unverifiable: { label: "Could not verify", variant: "outline", icon: WifiOff },
};

export function ChainVerificationBadge({
  status,
  explorerUrl,
}: {
  status: ChainVerificationStatus;
  explorerUrl?: string | null;
}) {
  const config = STATUS_CONFIG[status];
  if (!config) return null;
  const Icon = config.icon;

  const badge = (
    <Badge variant={config.variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  );

  if (!explorerUrl) return badge;

  return (
    <a
      href={explorerUrl}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 transition-opacity hover:opacity-80"
    >
      {badge}
      <ExternalLink className="h-3 w-3 text-muted-foreground" />
    </a>
  );
}
