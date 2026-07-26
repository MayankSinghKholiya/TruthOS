"use client";

import { motion } from "framer-motion";

import { Logo } from "@/components/layout/Logo";

const SUGGESTIONS = [
  "Is the current CJP protest movement anti-national?",
  "What is the current price of Bitcoin and Ethereum?",
  "Did water on Mars ever support microbial life?",
];

export function ChatEmptyState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-16 text-center"
    >
      <Logo iconOnly size={44} linkToHome={false} />
      <div className="flex flex-col gap-2">
        <h2 className="font-display text-2xl font-medium tracking-tight">
          What do you want to verify?
        </h2>
        <p className="max-w-md text-sm text-muted-foreground">
          TruthOS plans, researches, debates and verifies the answer before responding -
          separating fact from opinion, and showing its work.
        </p>
      </div>
      <div className="flex max-w-lg flex-wrap items-center justify-center gap-2">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => onSuggestion(suggestion)}
            className="glass rounded-full border border-border/60 px-4 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </motion.div>
  );
}
