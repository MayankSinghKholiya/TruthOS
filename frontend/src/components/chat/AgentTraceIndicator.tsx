"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Brain,
  Check,
  Compass,
  Database,
  Fingerprint,
  Gavel,
  PenLine,
  Search,
  ShieldCheck,
  Swords,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { AgentTraceEntry } from "@/store/chatStore";

const STAGES = [
  { key: "plan", label: "Planner", detail: "Decomposing your question into investigable sub-tasks", icon: Brain },
  { key: "gather", label: "Research & Retrieval", detail: "Searching the web and gathering evidence", icon: Search },
  { key: "verify", label: "Fact Checker", detail: "Verifying every claim strictly against the evidence", icon: ShieldCheck },
  { key: "critique", label: "Critic", detail: "Arguing skeptic and devil's advocate against the case", icon: Swords },
  { key: "reconcile", label: "Truth Engine", detail: "Separating verified fact from contested opinion", icon: Compass },
  { key: "judge", label: "Judge", detail: "Weighing every side to reach a final verdict", icon: Gavel },
  { key: "write", label: "Writer", detail: "Polishing the verdict into a clear, readable report", icon: PenLine },
  { key: "score_confidence", label: "Confidence DNA", detail: "Scoring diversity, freshness and consensus", icon: Fingerprint },
  { key: "commit_memory", label: "Memory", detail: "Committing this investigation to long-term memory", icon: Database },
];

export function AgentTraceIndicator({ trace }: { trace: AgentTraceEntry[] }) {
  const completedKeys = new Set(trace.map((t) => t.agentName));
  const completedCount = trace.length;
  const activeIndex = Math.min(completedCount, STAGES.length - 1);
  const activeStage = STAGES[activeIndex];
  const progressPct = (completedCount / (STAGES.length - 1)) * 100;

  return (
    <div className="glass rounded-2xl border border-border/60 p-5">
      <p className="mb-5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
        AI Courtroom in session
      </p>

      <div className="relative px-4">
        <div className="absolute inset-x-4 top-4 h-px bg-border/70" />
        <motion.div
          className="absolute left-4 top-4 h-px bg-gradient-to-r from-primary to-gold"
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
                  isDone && "border-transparent bg-gradient-to-br from-primary to-gold text-white",
                  isActive && "border-primary/50 bg-primary/15 text-primary shadow-glow",
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
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-gold/20 text-primary">
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
                className="h-1.5 w-1.5 rounded-full bg-primary"
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
