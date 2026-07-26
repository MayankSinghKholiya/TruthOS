"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, ClipboardCheck, Fingerprint, Gavel, History, Users } from "lucide-react";

import { cn } from "@/lib/utils";
import type { CourtTraceEntry } from "@/store/courtStore";

const STAGES = [
  { key: "fetch_reputation", label: "Pulling reputation history", detail: "Checking both wallets' prior standing", icon: History },
  { key: "build_case", label: "Claimant, Respondent & Evidence Verifier", detail: "Building both cases and checking the deliverable match, in parallel", icon: Users },
  { key: "arbitrate", label: "Arbitrator deliberating", detail: "Weighing both sides against the evidence", icon: Gavel },
  { key: "score_confidence", label: "Scoring confidence", detail: "Computing the verdict's Confidence DNA", icon: Fingerprint },
  { key: "persist", label: "Recording verdict & reputation", detail: "Finalizing the outcome for both wallets", icon: ClipboardCheck },
];

export function CourtTraceIndicator({ trace }: { trace: CourtTraceEntry[] }) {
  const completedKeys = new Set(trace.map((t) => t.nodeName));
  const completedCount = trace.length;
  const activeIndex = Math.min(completedCount, STAGES.length - 1);
  const activeStage = STAGES[activeIndex];
  const progressPct = (completedCount / (STAGES.length - 1)) * 100;

  return (
    <div className="glass rounded-2xl border border-gold/25 p-5">
      <p className="mb-5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
        TruthOS Court in session
      </p>

      <div className="relative px-4">
        <div className="absolute inset-x-4 top-4 h-px bg-border/70" />
        <motion.div
          className="absolute left-4 top-4 h-px bg-gradient-to-r from-gold to-primary"
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(progressPct, 100)}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          style={{ maxWidth: "calc(100% - 2rem)" }}
        />
        <div className="relative flex items-center justify-between">
          {STAGES.map((stage, i) => {
            const isDone = completedKeys.has(stage.key);
            const isActive = i === activeIndex && !isDone;
            const Icon = stage.icon;
            return (
              <motion.span
                key={stage.key}
                animate={isActive ? { scale: [1, 1.15, 1] } : { scale: 1 }}
                transition={
                  isActive ? { duration: 1.3, repeat: Infinity, ease: "easeInOut" } : { duration: 0.2 }
                }
                className={cn(
                  "relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border transition-colors duration-300",
                  isDone && "border-transparent bg-gradient-to-br from-gold to-primary text-white",
                  isActive &&
                    "border-gold/50 bg-gold/15 text-gold shadow-[0_0_0_1px_hsl(var(--gold)/0.2),0_0_20px_-4px_hsl(var(--gold)/0.5)]",
                  !isDone && !isActive && "border-border bg-background text-muted-foreground/40",
                )}
              >
                {isDone ? <Check className="h-4 w-4" /> : <Icon className="h-3.5 w-3.5" />}
              </motion.span>
            );
          })}
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeStage.key}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25 }}
          className="mt-5 flex items-center gap-3 rounded-xl bg-background/40 p-3.5"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-gold/20 to-primary/20 text-gold">
            <activeStage.icon className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium">{activeStage.label}</p>
            <p className="truncate text-xs text-muted-foreground">{activeStage.detail}</p>
          </div>
          <span className="ml-auto flex shrink-0 gap-1">
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                className="h-1.5 w-1.5 rounded-full bg-gold"
                animate={{ opacity: [0.25, 1, 0.25] }}
                transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
              />
            ))}
          </span>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
