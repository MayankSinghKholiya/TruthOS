"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { DisputeForm } from "@/components/court/DisputeForm";
import { ApiError, courtApi } from "@/lib/api";
import type { DisputeCreate } from "@/types";

export default function FileDisputePage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(payload: DisputeCreate) {
    setError(null);
    setIsSubmitting(true);
    try {
      const dispute = await courtApi.fileDispute(payload);
      router.push(`/court/${dispute.id}?arbitrate=1`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to file dispute");
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-10">
        <div>
          <h1 className="font-display text-3xl font-medium tracking-tight">File a dispute</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Describe what was agreed, what happened, and attach whatever evidence either side has.
            The AI Courtroom will build both cases and issue a neutral verdict.
          </p>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DisputeForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </div>
    </main>
  );
}
