export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  meta?: { report_id?: string | null } | null;
  report?: LayeredReport;
}

export interface EvidenceItem {
  claim: string;
  source_url: string | null;
  source_title: string | null;
  snippet: string;
  reliability: number;
}

export interface CounterArgument {
  argument: string;
  raised_by: string;
  strength: number;
}

export interface ConfidenceBreakdown {
  source_diversity: number;
  freshness: number;
  consensus: number;
  evidence_quality: number;
  retrieval_confidence: number;
  overall: number;
}

export interface ReferenceItem {
  title: string;
  url: string | null;
  published_at: string | null;
}

export interface AgentTraceStep {
  agent: string;
  status: string;
  confidence: number;
  model_used: string | null;
  retries_used: number;
}

export interface EntityAmbiguity {
  is_ambiguous: boolean;
  explanation: string;
}

export interface LayeredReport {
  id: string | null;
  query: string;
  verdict: string;
  executive_summary: string;
  confidence: ConfidenceBreakdown;
  evidence: EvidenceItem[];
  counter_arguments: CounterArgument[];
  deep_dive: string;
  references: ReferenceItem[];
  agent_trace: AgentTraceStep[];
  entity_ambiguity?: EntityAmbiguity | null;
  created_at: string | null;
}

export interface StreamEvent {
  type: "agent_started" | "agent_completed" | "token" | "report_ready" | "error";
  agent_name: string | null;
  data: Record<string, unknown>;
}

// ---- TruthOS Court (dispute arbitration) ----

export const SUPPORTED_CHAINS = ["ethereum", "base", "bsc", "polygon", "arbitrum", "xlayer"] as const;
export type SupportedChain = (typeof SUPPORTED_CHAINS)[number];

export type ChainVerificationStatus =
  | "confirmed_match"
  | "confirmed_mismatch"
  | "confirmed"
  | "failed_onchain"
  | "pending"
  | "not_found"
  | "invalid_format"
  | "unsupported_chain"
  | "unverifiable";

export interface ChainVerification {
  status: ChainVerificationStatus;
  chain: string | null;
  tx_hash: string | null;
  explorer_url: string | null;
  from_address: string | null;
  to_address: string | null;
  value_native: number | null;
  block_number: number | null;
  claimed_amount: number | null;
  reason: string | null;
  supported_chains: string[] | null;
}

export interface EvidenceInput {
  submitted_by: "claimant" | "respondent";
  evidence_type: string;
  content: string;
  url?: string | null;
  chain?: string | null;
}

export interface DisputeEvidenceRead {
  id: string;
  submitted_by: string;
  evidence_type: string;
  content: string;
  url: string | null;
  chain: string | null;
  verification_status: ChainVerificationStatus | null;
  verification_details: Record<string, unknown> | null;
  created_at: string;
}

export interface DisputeCreate {
  claimant_wallet_id: string;
  respondent_wallet_id: string;
  task_description: string;
  agreed_deliverable: string;
  actual_deliverable: string;
  escrow_amount?: number | null;
  evidence: EvidenceInput[];
}

export interface Dispute {
  id: string;
  claimant_wallet_id: string;
  respondent_wallet_id: string;
  task_description: string;
  agreed_deliverable: string;
  actual_deliverable: string;
  escrow_amount: number | null;
  status: "open" | "resolved" | "failed";
  created_at: string;
  evidence: DisputeEvidenceRead[];
}

export interface EvidenceTimelineEntry {
  submitted_by: string;
  evidence_type: string;
  summary: string;
  weight: number;
}

export interface DisputeVerdict {
  id: string | null;
  dispute_id: string;
  verdict: string;
  claimant_fault_percentage: number;
  respondent_fault_percentage: number;
  refund_recommendation_percentage: number;
  executive_summary: string;
  reasoning: string;
  confidence_score: number;
  confidence_breakdown: {
    evidence_completeness: number;
    evidence_decisiveness: number;
    narrative_consensus: number;
    chain_evidence_integrity: number;
    overall: number;
  };
  evidence_timeline: EvidenceTimelineEntry[];
  counter_arguments: CounterArgument[];
  agent_trace: AgentTraceStep[];
  created_at: string | null;
}

export interface Reputation {
  wallet_id: string;
  trust_score: number;
  disputes_total: number;
  disputes_at_fault: number;
  avg_fault_percentage: number;
  completed_tasks: number;
  standing: "Trusted" | "Neutral" | "Flagged";
}

export interface DisputeHistoryEntry {
  dispute_id: string;
  role: "claimant" | "respondent";
  task_description: string;
  status: "open" | "resolved" | "failed";
  verdict: string | null;
  fault_percentage: number | null;
  created_at: string;
}

// ---- Agent-callable API keys ----

export interface ApiKeyCreate {
  wallet_id: string;
  label?: string | null;
}

export interface ApiKeyCreated {
  id: string;
  key: string;
  key_prefix: string;
  wallet_id: string;
  label: string | null;
  created_at: string;
}

export interface ApiKeyRead {
  id: string;
  key_prefix: string;
  wallet_id: string;
  label: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

// ---- Telegram notifications ----

export interface TelegramLinkStart {
  code: string;
  bot_username: string | null;
  expires_in_seconds: number;
}

export interface TelegramLinkStatus {
  linked: boolean;
  telegram_username: string | null;
  linked_at: string | null;
}

export interface WalletWatchCreate {
  wallet_id: string;
  label?: string | null;
}

export interface WalletWatchRead {
  id: string;
  wallet_id: string;
  label: string | null;
  created_at: string;
}
