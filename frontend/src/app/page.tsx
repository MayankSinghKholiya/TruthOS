"use client";

import { motion } from "framer-motion";
import {
  AlertOctagon,
  ArrowRight,
  Bot,
  Brain,
  Check,
  CheckCircle2,
  Compass,
  Database,
  Fingerprint,
  Gavel,
  History,
  Link2,
  Network,
  PenLine,
  Search,
  Send,
  ShieldAlert,
  ShieldCheck,
  Swords,
  User,
  UserRound,
  Webhook,
  Wrench,
} from "lucide-react";
import Link from "next/link";

import { CodeBlock } from "@/components/landing/CodeBlock";
import { PipelineDiagram, type PipelineStage } from "@/components/landing/PipelineDiagram";
import { SampleArbitrationCard } from "@/components/landing/SampleArbitrationCard";
import { SampleVerdictCard } from "@/components/landing/SampleVerdictCard";
import { TelegramPreview } from "@/components/landing/TelegramPreview";
import { Logo } from "@/components/layout/Logo";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Button } from "@/components/ui/button";

const CHAT_STAGES: PipelineStage[] = [
  {
    index: "01",
    title: "Plan",
    summary:
      "A Planner agent breaks your question into sub-tasks and assigns each one to whichever specialist actually fits it.",
    lanes: [
      {
        icon: Brain,
        agent: "Planner",
        detail: "Decomposes the query and routes each sub-task to Research, Finance, Legal, or Coder.",
      },
    ],
  },
  {
    index: "02",
    title: "Gather",
    summary: "Every sub-task pulls its own evidence, and every sub-task runs at the same time as the others.",
    lanes: [
      {
        icon: Search,
        agent: "Retriever",
        detail: "Expands the sub-task into targeted search queries, plus recency and domain filters - cross-referencing a knowledge graph of prior investigations when the topic calls for it, so a recurring or ambiguous entity doesn't get re-guessed from scratch.",
      },
      {
        icon: Database,
        agent: "Hybrid retrieval",
        detail:
          "BM25 keyword search, Qdrant dense vectors, and live web search are fused with Reciprocal Rank Fusion, then re-ordered by a cross-encoder for the final ranking.",
      },
      {
        icon: Wrench,
        agent: "Specialist",
        detail: "Finance, Legal, or Coder steps in when a sub-task needs live market data, statute-level reasoning, or code - not just prose.",
      },
    ],
  },
  {
    index: "03",
    title: "Verify",
    summary: "Every claim gets checked against the evidence that was actually retrieved for it - nothing else.",
    lanes: [
      {
        icon: ShieldCheck,
        agent: "Fact Checker",
        detail: "Runs at zero temperature by design - deterministic verification, no stylistic drift.",
      },
    ],
  },
  {
    index: "04",
    title: "Critique",
    summary: "One agent, two adversarial roles, arguing against the claims on purpose.",
    lanes: [
      {
        icon: Swords,
        agent: "Critic",
        detail: "Plays the Skeptic, who attacks weak evidence, and the Devil's Advocate, who argues the opposite conclusion.",
      },
    ],
  },
  {
    index: "05",
    title: "Reconcile",
    summary: "Fact is separated from opinion, and what's still unresolved is named instead of smoothed over.",
    lanes: [
      {
        icon: Compass,
        agent: "Truth Engine",
        detail: "Also checks whether the question's own subject is ambiguous or conflated with something else, before an answer is even attempted.",
      },
    ],
  },
  {
    index: "06",
    title: "Judge",
    summary: "A single verdict, reached by the platform's strongest reasoning model.",
    lanes: [
      {
        icon: Gavel,
        agent: "Judge",
        detail: "Weighs every prior stage. Direct evidence always outranks precedent, prior turns, or stylistic confidence.",
      },
    ],
  },
  {
    index: "07",
    title: "Write",
    summary: "The verdict becomes readable - without becoming a different verdict.",
    lanes: [
      {
        icon: PenLine,
        agent: "Writer",
        detail: "Rephrases and formats only. Not permitted to introduce a single claim the Judge didn't already make.",
      },
    ],
  },
  {
    index: "08",
    title: "Score",
    summary: "Confidence isn't a vibe - it's five weighted signals, shown to you, not hidden behind the answer.",
    lanes: [
      {
        icon: Fingerprint,
        agent: "Confidence DNA",
        detail: "Source diversity, freshness, consensus, evidence quality, and retrieval relevance - one weak signal can't hide behind the others.",
      },
    ],
  },
  {
    index: "09",
    title: "Remember",
    summary: "What mattered gets kept, so the next related question starts smarter instead of from zero.",
    lanes: [
      {
        icon: Network,
        agent: "Memory + Knowledge Graph",
        detail: "A Memory agent decides what's worth keeping; entities and relationships are also extracted into a Neo4j graph.",
      },
    ],
  },
];

const COURT_STAGES: PipelineStage[] = [
  {
    index: "01",
    title: "Check history",
    summary: "Both wallets' trust score and dispute record are pulled before anything else is decided.",
    lanes: [
      {
        icon: History,
        agent: "Reputation store",
        detail: "Context for the arbitrator - not a verdict by itself.",
      },
    ],
  },
  {
    index: "02",
    title: "Build the case",
    summary: "Three agents work the same evidence from three different angles, at the same time.",
    lanes: [
      {
        icon: User,
        agent: "Claimant",
        detail: "Builds the strongest good-faith case for whoever filed the dispute.",
      },
      {
        icon: UserRound,
        agent: "Respondent",
        detail: "Builds the strongest good-faith defense for the other party.",
      },
      {
        icon: Link2,
        agent: "Evidence Verifier",
        detail:
          "An objective, no-side pass on whether the deliverable matches what was agreed. Any cited transaction is checked against the real chain - Ethereum, Base, BSC, Polygon, Arbitrum, or XLayer - not taken on either party's word.",
      },
    ],
  },
  {
    index: "03",
    title: "Arbitrate",
    summary: "One neutral authority weighs all three. Reputation is a tiebreaker, never the deciding vote.",
    lanes: [
      {
        icon: Gavel,
        agent: "Arbitrator",
        detail: "A low-trust party can still be right this time, and a trusted one can still be at fault - direct evidence always wins.",
      },
    ],
  },
  {
    index: "04",
    title: "Score confidence",
    summary: "Four signals this time, including one no text-only arbitrator can fake.",
    lanes: [
      {
        icon: Fingerprint,
        agent: "Confidence DNA",
        detail: "Evidence completeness, decisiveness, narrative consensus, and chain evidence integrity - a fabricated transaction drags the score down on its own.",
      },
    ],
  },
  {
    index: "05",
    title: "Resolve",
    summary: "Verdict, fault split, and refund recommendation are recorded, and both reputations update.",
    lanes: [
      {
        icon: CheckCircle2,
        agent: "Verdict + reputation update",
        detail: "How much this one dispute can move a trust score scales with the verdict's own confidence and the escrow at stake - a coin-flip call over a trivial amount doesn't swing a score the way a decisive, high-value one does. The dispute becomes part of the public record other counterparties can check before they engage either wallet.",
      },
    ],
  },
];

const TELEGRAM_TRIGGERS = [
  {
    icon: ShieldAlert,
    title: "Dispute filed",
    description:
      "The instant someone opens a dispute against a wallet you're watching - who filed it, what the task was, when it happened.",
  },
  {
    icon: AlertOctagon,
    title: "Counterparty flagged",
    description:
      "A dispute you were party to resolves and the other side's trust score drops to Flagged - you're told immediately, verdict included.",
  },
  {
    icon: Send,
    title: "Interacted without checking",
    description:
      "Your agent deals with an already-Flagged wallet without a safety check first - you find out anyway, no watch required for your own agent's wallet.",
  },
  {
    icon: Search,
    title: "Safety check pinged",
    description:
      "Run a reputation check yourself, or have your agent run one via API - a Flagged result reaches Telegram too, for when the checker has no screen to show a warning on.",
  },
];

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-mesh">
      <div className="bg-grain absolute inset-0" />

      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Logo size={44} />
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <Button variant="ghost" size="sm" asChild>
            <Link href="/login">
              Sign in <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex max-w-5xl flex-col items-center gap-28 px-6 pb-32 pt-12 text-center sm:pt-20">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="flex flex-col items-center gap-7"
        >
          <span className="glass shadow-glow inline-flex items-center gap-2 rounded-full border border-border/60 px-4 py-1.5 text-xs font-medium text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            Evidence-Driven Multi-Agent Intelligence
          </span>
          <h1 className="max-w-3xl font-display text-5xl font-medium leading-[1.08] tracking-tight sm:text-6xl">
            Build the most trustworthy AI,
            <br />
            not the <em className="text-gradient font-medium italic">fastest</em> one.
          </h1>
          <p className="max-w-xl text-balance text-lg text-muted-foreground">
            TruthOS plans, researches, verifies, debates and explains every important answer -
            separating fact from opinion and showing its work.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Button size="lg" asChild>
              <Link href="/chat">
                Start an investigation <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" className="glass" asChild>
              <Link href="/court">Explore TruthOS Court</Link>
            </Button>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 pt-6 text-xs text-muted-foreground">
            {[
              "16 specialist agents across two pipelines",
              "Live on-chain evidence checks",
              "Built for humans and autonomous agents",
              "Telegram alerts on flagged activity",
            ].map((item) => (
              <span key={item} className="flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5 text-primary" /> {item}
              </span>
            ))}
          </div>
        </motion.div>

        <section className="flex w-full flex-col gap-10 text-left">
          <SectionHeading
            eyebrow="The AI Courtroom"
            title="Nine stages between your question and a verdict."
            description="Not a single model's best guess - a pipeline that plans, retrieves, verifies, argues both sides of itself, and only then writes an answer."
          />
          <PipelineDiagram stages={CHAT_STAGES} />
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5 }}
          >
            <SampleVerdictCard />
          </motion.div>
          <p className="rounded-xl border border-border/60 bg-card/40 p-4 text-sm leading-relaxed text-muted-foreground">
            Disagree with a verdict? Challenge it directly from the report - your objection re-opens
            the investigation instead of starting a new conversation from zero.
          </p>
        </section>

        <section className="flex w-full flex-col gap-10 text-left">
          <SectionHeading
            eyebrow="TruthOS Court"
            title="An AI arbitrator for agent-to-agent work."
            description="Built the way a real court is - evidence first, reputation second. Resolves disputes between any two wallets over a task that was agreed, delivered, and disputed."
          />
          <PipelineDiagram stages={COURT_STAGES} />
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5 }}
          >
            <SampleArbitrationCard />
          </motion.div>
          <p className="rounded-xl border border-border/60 bg-card/40 p-4 text-sm leading-relaxed text-muted-foreground">
            Before you deal with any wallet, its full dispute history is a public lookup - not just a
            trust score, the actual verdicts behind it.
          </p>
        </section>

        <section className="flex w-full flex-col gap-10 text-left">
          <SectionHeading
            eyebrow="Telegram Alerts"
            title="Connect your agent, then stop watching it yourself."
            description="The moment a wallet you're watching is disputed, deals with a counterparty who just got Flagged, or gets checked and comes back risky - you hear about it on Telegram, not by refreshing a dashboard."
          />
          <div className="grid gap-4 sm:grid-cols-2">
            {TELEGRAM_TRIGGERS.map((trigger, i) => {
              const Icon = trigger.icon;
              return (
                <motion.div
                  key={trigger.title}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-80px" }}
                  transition={{ duration: 0.5, delay: i * 0.06 }}
                  className="group flex flex-col gap-3 rounded-xl border border-border/60 bg-card/40 p-5 transition-all duration-200 hover:-translate-y-1 hover:border-primary/50 hover:shadow-glow"
                >
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary/25 to-gold/20 text-primary transition-transform duration-200 group-hover:scale-110">
                    <Icon className="h-4 w-4" />
                  </span>
                  <h3 className="font-display text-base font-medium">{trigger.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">{trigger.description}</p>
                </motion.div>
              );
            })}
          </div>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5 }}
            className="mx-auto w-full max-w-md"
          >
            <TelegramPreview />
          </motion.div>
          <p className="rounded-xl border border-border/60 bg-card/40 p-4 text-center text-sm leading-relaxed text-muted-foreground">
            That&apos;s not a mockup - it&apos;s the literal output of the same formatter that ships the real alerts.
          </p>
        </section>

        <section className="flex w-full flex-col gap-10 text-left">
          <SectionHeading
            eyebrow="Human + Agent"
            title="Two front doors. One arbitration engine."
            description="Every verdict TruthOS Court reaches is reachable two ways - a human dashboard, and a plain API another agent can call entirely on its own."
          />
          <div className="grid gap-4 lg:grid-cols-2">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5 }}
              className="group flex flex-col gap-4 rounded-xl border border-border/60 bg-card/40 p-6 transition-all duration-200 hover:-translate-y-1 hover:border-primary/50 hover:shadow-glow"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary/25 to-gold/20 text-primary">
                <User className="h-5 w-5" />
              </span>
              <h3 className="font-display text-lg font-medium">For humans</h3>
              <ul className="flex flex-col gap-2.5 text-sm text-muted-foreground">
                <li>File a dispute through the Court dashboard and watch arbitration run live, stage by stage.</li>
                <li>Run a red-flag check on a counterparty&apos;s wallet before you ever engage them.</li>
                <li>Challenge a research verdict inline and get a re-investigation, not a canned reply.</li>
                <li>Get a Telegram alert for any wallet you watch - a dispute filed, or a counterparty going Flagged.</li>
              </ul>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: 0.08 }}
              className="group flex flex-col gap-4 rounded-xl border border-border/60 bg-card/40 p-6 transition-all duration-200 hover:-translate-y-1 hover:border-primary/50 hover:shadow-glow"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary/25 to-gold/20 text-primary">
                <Bot className="h-5 w-5" />
              </span>
              <h3 className="font-display text-lg font-medium">For agents</h3>
              <ul className="flex flex-col gap-2.5 text-sm text-muted-foreground">
                <li>An API-key-authenticated endpoint files a dispute and starts arbitration immediately - no browser, no login session.</li>
                <li>Idempotent by design, so a retried call can&apos;t double-file the same dispute.</li>
                <li>Optionally notifies a webhook the moment a verdict lands, instead of making the caller poll.</li>
              </ul>
            </motion.div>
          </div>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.5, delay: 0.16 }}
            className="grid items-center gap-6 lg:grid-cols-2"
          >
            <CodeBlock
              label="POST /api/v1/disputes/agent"
              code={`curl https://api.truthos.dev/api/v1/disputes/agent \\
  -H "X-API-Key: toc_your_agent_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "respondent_wallet_id": "0x9f2c...",
    "task_description": "Logo design task, 250 USDC escrow",
    "agreed_deliverable": "SVG logo, on payment confirmation",
    "actual_deliverable": "Nothing delivered - payment disputed",
    "escrow_amount": 250,
    "evidence": [{
      "submitted_by": "claimant",
      "evidence_type": "tx_reference",
      "chain": "base",
      "content": "0xdeadbeef... (cited as payment proof)"
    }],
    "callback_url": "https://your-agent.example/webhook"
  }'`}
            />
            <div className="flex flex-col gap-3">
              <div className="flex items-start gap-3">
                <Webhook className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <p className="text-sm leading-relaxed text-muted-foreground">
                  This is the shape of integration OKX&apos;s agent-to-agent (A2A) model is built
                  around - any OKX AI agent, or any agent from any ecosystem, can hold a TruthOS
                  Court API key and resolve a dispute entirely on its own, no human in the loop.
                </p>
              </div>
              <div className="flex items-start gap-3">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Same evidence pipeline, same on-chain checks, same Confidence DNA score as the
                  human dashboard - an agent gets no shortcuts and no separate, lighter-weight verdict.
                </p>
              </div>
            </div>
          </motion.div>
        </section>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5 }}
          className="glass shadow-glow flex w-full flex-col items-center gap-5 rounded-2xl border border-border/60 p-10 text-center"
        >
          <h2 className="font-display text-2xl font-medium tracking-tight sm:text-3xl">
            Ask something that actually matters.
          </h2>
          <p className="max-w-md text-sm text-muted-foreground">
            See the full pipeline run - plan, evidence, debate, verdict, and the confidence score
            behind it.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button size="lg" asChild>
              <Link href="/chat">
                Start an investigation <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" className="glass" asChild>
              <Link href="/court">Explore TruthOS Court</Link>
            </Button>
          </div>
        </motion.div>
      </main>

      <footer className="relative z-10 mx-auto max-w-6xl px-6 pb-10 text-center text-xs text-muted-foreground">
        TruthOS - Evidence-Driven Multi-Agent Intelligence Platform
      </footer>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5 }}
      className="flex flex-col gap-3"
    >
      <span className="text-xs font-semibold uppercase tracking-wider text-primary">{eyebrow}</span>
      <h2 className="font-display text-2xl font-medium tracking-tight sm:text-3xl">{title}</h2>
      <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</p>
    </motion.div>
  );
}
