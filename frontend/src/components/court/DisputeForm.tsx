"use client";

import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { RespondentRiskCheck } from "@/components/court/RespondentRiskCheck";
import { TxEvidenceCheck } from "@/components/court/TxEvidenceCheck";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { SUPPORTED_CHAINS, type DisputeCreate, type EvidenceInput } from "@/types";

interface DisputeFormProps {
  onSubmit: (payload: DisputeCreate) => void;
  isSubmitting?: boolean;
}

const EMPTY_EVIDENCE: EvidenceInput = {
  submitted_by: "claimant",
  evidence_type: "chat_log",
  content: "",
  url: "",
};

export function DisputeForm({ onSubmit, isSubmitting }: DisputeFormProps) {
  const [claimantWalletId, setClaimantWalletId] = useState("");
  const [respondentWalletId, setRespondentWalletId] = useState("");
  const [escrowAmount, setEscrowAmount] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [agreedDeliverable, setAgreedDeliverable] = useState("");
  const [actualDeliverable, setActualDeliverable] = useState("");
  const [evidence, setEvidence] = useState<EvidenceInput[]>([{ ...EMPTY_EVIDENCE }]);

  function updateEvidence(index: number, patch: Partial<EvidenceInput>) {
    setEvidence((prev) => prev.map((e, i) => (i === index ? { ...e, ...patch } : e)));
  }

  function addEvidence() {
    setEvidence((prev) => [...prev, { ...EMPTY_EVIDENCE }]);
  }

  function removeEvidence(index: number) {
    setEvidence((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      claimant_wallet_id: claimantWalletId.trim(),
      respondent_wallet_id: respondentWalletId.trim(),
      task_description: taskDescription.trim(),
      agreed_deliverable: agreedDeliverable.trim(),
      actual_deliverable: actualDeliverable.trim(),
      escrow_amount: escrowAmount.trim() ? Number(escrowAmount) : null,
      evidence: evidence.filter((ev) => ev.content.trim().length > 0),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Parties &amp; escrow</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="claimant">Claimant wallet ID</Label>
            <Input
              id="claimant"
              required
              placeholder="0x... (the party filing this dispute)"
              value={claimantWalletId}
              onChange={(e) => setClaimantWalletId(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="respondent">Respondent wallet ID</Label>
            <Input
              id="respondent"
              required
              placeholder="0x... (the party being disputed against)"
              value={respondentWalletId}
              onChange={(e) => setRespondentWalletId(e.target.value)}
            />
            <RespondentRiskCheck walletId={respondentWalletId} />
          </div>
          <div className="flex flex-col gap-1.5 sm:col-span-2">
            <Label htmlFor="escrow">Escrow amount (optional)</Label>
            <Input
              id="escrow"
              type="number"
              min="0"
              step="0.01"
              placeholder="e.g. 250"
              value={escrowAmount}
              onChange={(e) => setEscrowAmount(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>What was agreed vs. what happened</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="task">Task description</Label>
            <Textarea
              id="task"
              required
              placeholder="What was the respondent hired to do?"
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="agreed">Agreed deliverable (SOW)</Label>
            <Textarea
              id="agreed"
              required
              placeholder="What was promised, as specifically as possible"
              value={agreedDeliverable}
              onChange={(e) => setAgreedDeliverable(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="actual">Actual deliverable</Label>
            <Textarea
              id="actual"
              required
              placeholder="What was actually delivered, per the claimant"
              value={actualDeliverable}
              onChange={(e) => setActualDeliverable(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>Evidence</CardTitle>
          <Button type="button" variant="outline" size="sm" onClick={addEvidence}>
            <Plus className="h-4 w-4" /> Add evidence
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {evidence.map((item, index) => (
            <div key={index} className="flex flex-col gap-3 rounded-lg border border-border p-4">
              <div className="flex items-center justify-between">
                <div className="flex gap-2">
                  <select
                    className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                    value={item.submitted_by}
                    onChange={(e) =>
                      updateEvidence(index, { submitted_by: e.target.value as "claimant" | "respondent" })
                    }
                  >
                    <option value="claimant">Submitted by claimant</option>
                    <option value="respondent">Submitted by respondent</option>
                  </select>
                  <select
                    className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                    value={item.evidence_type}
                    onChange={(e) => updateEvidence(index, { evidence_type: e.target.value })}
                  >
                    <option value="chat_log">Chat log</option>
                    <option value="deliverable">Deliverable</option>
                    <option value="tx_reference">On-chain tx reference</option>
                    <option value="document">Document</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                {evidence.length > 1 && (
                  <Button type="button" variant="ghost" size="icon" onClick={() => removeEvidence(index)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
              {item.evidence_type === "tx_reference" && (
                <select
                  className="h-9 w-fit rounded-md border border-input bg-background px-2 text-sm"
                  value={item.chain ?? ""}
                  onChange={(e) => updateEvidence(index, { chain: e.target.value })}
                >
                  <option value="" disabled>
                    Select chain...
                  </option>
                  {SUPPORTED_CHAINS.map((chain) => (
                    <option key={chain} value={chain}>
                      {chain}
                    </option>
                  ))}
                </select>
              )}
              <Textarea
                placeholder={
                  item.evidence_type === "tx_reference"
                    ? "Paste the transaction hash (0x...)"
                    : "Paste the evidence content here (chat excerpt, description of the file, tx hash, etc.)"
                }
                value={item.content}
                onChange={(e) => updateEvidence(index, { content: e.target.value })}
              />
              {item.evidence_type === "tx_reference" && item.chain && (
                <TxEvidenceCheck
                  chain={item.chain}
                  content={item.content}
                  escrowAmount={escrowAmount.trim() ? Number(escrowAmount) : null}
                />
              )}
              <Input
                placeholder="Optional URL (e.g. link to file or block explorer)"
                value={item.url ?? ""}
                onChange={(e) => updateEvidence(index, { url: e.target.value })}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Button type="submit" size="lg" disabled={isSubmitting}>
        {isSubmitting ? "Filing dispute..." : "File dispute & start arbitration"}
      </Button>
    </form>
  );
}
