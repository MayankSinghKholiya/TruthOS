"use client";

import { motion } from "framer-motion";
import { ArrowRight, Gavel, Scale, ShieldCheck, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCourtStore } from "@/store/courtStore";

const STATUS_VARIANT: Record<string, "success" | "secondary" | "destructive"> = {
  resolved: "success",
  open: "secondary",
  failed: "destructive",
};

export default function CourtDashboardPage() {
  const router = useRouter();
  const disputes = useCourtStore((s) => s.disputes);

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="relative overflow-hidden border-b border-border/70">
        <div className="bg-mesh bg-grain absolute inset-0" />
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative z-10 mx-auto flex max-w-4xl flex-col gap-4 px-6 py-14"
        >
          <span className="glass inline-flex w-fit items-center gap-2 rounded-full border border-border/60 px-3.5 py-1.5 text-xs font-medium text-muted-foreground">
            <Scale className="h-3.5 w-3.5 text-gold" /> TruthOS Court
          </span>
          <h1 className="max-w-xl font-display text-4xl font-medium leading-tight tracking-tight">
            Neutral AI arbitration for <span className="text-gradient italic">agent-to-agent</span>{" "}
            work
          </h1>
          <p className="max-w-2xl text-muted-foreground">
            File a dispute when an escrowed task didn&apos;t go as agreed. Claimant and Respondent
            agents each argue their case, an Evidence Verifier checks the deliverable objectively,
            and a neutral Arbitrator issues a fault split and refund recommendation - with a
            transparent confidence score.
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Button size="lg" variant="gold" onClick={() => router.push("/court/file")}>
              <Gavel className="h-4 w-4" /> File a dispute
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="glass"
              onClick={() => router.push("/court/reputation")}
            >
              <ShieldCheck className="h-4 w-4" /> Check a wallet&apos;s trust score
            </Button>
          </div>
        </motion.div>
      </div>

      <div className="mx-auto flex max-w-4xl flex-col gap-4 px-6 py-10">
        <h2 className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Sparkles className="h-4 w-4" /> Recent disputes
        </h2>
        {disputes.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              No disputes filed yet. File one to see the AI arbitration pipeline in action.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {disputes.map((dispute) => (
              <Card
                key={dispute.id}
                className="group cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:border-gold/50 hover:shadow-[0_0_0_1px_hsl(var(--gold)/0.15),0_8px_24px_-8px_hsl(var(--gold)/0.35)]"
                onClick={() => router.push(`/court/${dispute.id}`)}
              >
                <CardHeader className="flex-row items-start justify-between space-y-0">
                  <CardTitle className="text-sm font-medium leading-snug">
                    {dispute.task_description}
                  </CardTitle>
                  <Badge variant={STATUS_VARIANT[dispute.status] ?? "secondary"} className="capitalize">
                    {dispute.status}
                  </Badge>
                </CardHeader>
                <CardContent className="flex flex-col gap-1 text-xs text-muted-foreground">
                  <span className="truncate font-mono">Claimant: {dispute.claimant_wallet_id}</span>
                  <span className="truncate font-mono">Respondent: {dispute.respondent_wallet_id}</span>
                  <span className="mt-2 flex items-center gap-1 text-gold opacity-0 transition-opacity group-hover:opacity-100">
                    View verdict <ArrowRight className="h-3 w-3" />
                  </span>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
