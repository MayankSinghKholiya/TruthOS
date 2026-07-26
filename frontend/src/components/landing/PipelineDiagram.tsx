"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

export interface PipelineLane {
  icon: LucideIcon;
  agent: string;
  detail: string;
}

export interface PipelineStage {
  index: string;
  title: string;
  summary: string;
  lanes: PipelineLane[];
}

/** A vertical, numbered pipeline: one card per stage, connected by a single
 * gradient line. Stages with more than one lane render those lanes
 * side-by-side to show they execute concurrently, not in sequence - the
 * actual shape of both TruthOS orchestrators (LangGraph nodes that fan out
 * to parallel agent calls, then fan back in). */
export function PipelineDiagram({ stages }: { stages: PipelineStage[] }) {
  return (
    <div className="relative flex flex-col">
      <div className="absolute bottom-6 left-[19px] top-6 w-px bg-gradient-to-b from-primary/50 via-primary/20 to-transparent sm:left-[23px]" />
      {stages.map((stage, i) => (
        <motion.div
          key={stage.index}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, delay: i * 0.06 }}
          className="relative flex gap-5 pb-10 last:pb-0 sm:gap-6"
        >
          <span className="glass shadow-glow relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-primary/30 font-display text-sm font-semibold text-primary sm:h-12 sm:w-12">
            {stage.index}
          </span>
          <div className="flex min-w-0 flex-1 flex-col gap-3 pt-1">
            <div>
              <h3 className="font-display text-lg font-medium tracking-tight sm:text-xl">
                {stage.title}
              </h3>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{stage.summary}</p>
            </div>
            <div
              className={`grid gap-3 ${
                stage.lanes.length > 1 ? "sm:grid-cols-2 lg:grid-cols-3" : "sm:grid-cols-1"
              }`}
            >
              {stage.lanes.map((lane) => {
                const Icon = lane.icon;
                return (
                  <div
                    key={lane.agent}
                    className="group relative flex flex-col gap-2 rounded-lg border border-border/60 bg-card/40 p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/50 hover:bg-card/70 hover:shadow-glow"
                  >
                    <div className="flex items-center gap-2">
                      <span className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-primary/25 to-gold/20 text-primary transition-transform duration-200 group-hover:scale-110">
                        <Icon className="h-3.5 w-3.5" />
                      </span>
                      <span className="text-sm font-semibold">{lane.agent}</span>
                    </div>
                    <p className="text-xs leading-relaxed text-muted-foreground">{lane.detail}</p>
                  </div>
                );
              })}
            </div>
            {stage.lanes.length > 1 && (
              <span className="w-fit rounded-full bg-muted px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">
                Runs concurrently
              </span>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
