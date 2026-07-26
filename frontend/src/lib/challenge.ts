import type { LayeredReport } from "@/types";

/** Turns a user's pushback on a report into a new investigation query that
 * carries enough context (the original question + verdict) for the Planner
 * to actually re-investigate the specific point being challenged, rather
 * than starting from a blank slate. */
export function composeChallengeQuery(report: LayeredReport, challengeText: string): string {
  return [
    `I previously asked: "${report.query}"`,
    `TruthOS's verdict was: "${report.verdict}"`,
    "",
    `I want to challenge or re-verify this specific point: "${challengeText}"`,
    "",
    "Please re-investigate specifically addressing my concern, and confirm, revise, or update the verdict accordingly.",
  ].join("\n");
}
