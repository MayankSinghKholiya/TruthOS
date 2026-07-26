"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";

import { CourtTraceIndicator } from "@/components/court/CourtTraceIndicator";
import { SubmittedEvidenceList } from "@/components/court/SubmittedEvidenceList";
import { VerdictView } from "@/components/court/VerdictView";
import { courtApi, streamArbitration } from "@/lib/api";
import { useCourtStore } from "@/store/courtStore";
import type { DisputeVerdict, StreamEvent } from "@/types";

export default function DisputeDetailPage() {
  const params = useParams<{ disputeId: string }>();
  const searchParams = useSearchParams();
  const disputeId = params.disputeId;
  const shouldArbitrate = searchParams.get("arbitrate") === "1";

  const currentDispute = useCourtStore((s) => s.currentDispute);
  const currentVerdict = useCourtStore((s) => s.currentVerdict);
  const isArbitrating = useCourtStore((s) => s.isArbitrating);
  const trace = useCourtStore((s) => s.trace);
  const error = useCourtStore((s) => s.error);
  const hasStarted = useRef(false);

  useEffect(() => {
    useCourtStore.getState().reset();
    hasStarted.current = false;

    courtApi
      .getDispute(disputeId)
      .then((dispute) => {
        useCourtStore.getState().setCurrentDispute(dispute);

        if (dispute.status === "resolved") {
          courtApi
            .getVerdict(disputeId)
            .then((verdict) => useCourtStore.getState().finishArbitrating(verdict))
            .catch(() => undefined);
        } else if (shouldArbitrate && !hasStarted.current) {
          hasStarted.current = true;
          runArbitration();
        }
      })
      .catch(() => useCourtStore.getState().setError("Could not load this dispute."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disputeId]);

  async function runArbitration() {
    useCourtStore.getState().startArbitrating();
    try {
      await streamArbitration(disputeId, (event: StreamEvent) => {
        if (event.type === "agent_completed" && event.agent_name) {
          useCourtStore.getState().pushTraceStep(event.agent_name);
        }
        if (event.type === "report_ready") {
          useCourtStore.getState().finishArbitrating(event.data as unknown as DisputeVerdict);
        }
        if (event.type === "error") {
          useCourtStore.getState().setError((event.data.message as string) ?? "Arbitration failed");
        }
      });
    } catch {
      useCourtStore.getState().setError("Failed to reach TruthOS Court. Is the backend running?");
    }
  }

  if (!currentDispute) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">
          {error ?? "Loading dispute..."}
        </p>
      </main>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
        <div>
          <h1 className="text-xl font-semibold">{currentDispute.task_description}</h1>
          <p className="font-mono text-sm text-muted-foreground">
            {currentDispute.claimant_wallet_id} <span className="mx-1">vs.</span>{" "}
            {currentDispute.respondent_wallet_id}
          </p>
        </div>

        {isArbitrating && <CourtTraceIndicator trace={trace} />}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {currentVerdict && !isArbitrating && (
          <VerdictView dispute={currentDispute} verdict={currentVerdict} />
        )}
        {!isArbitrating && !currentVerdict && !error && currentDispute.status === "open" && (
          <p className="text-sm text-muted-foreground">This dispute hasn&apos;t been arbitrated yet.</p>
        )}

        {!isArbitrating && (
          <div className="flex flex-col gap-2">
            <h2 className="text-sm font-semibold text-muted-foreground">Submitted evidence</h2>
            <SubmittedEvidenceList evidence={currentDispute.evidence} />
          </div>
        )}
      </div>
    </main>
  );
}
