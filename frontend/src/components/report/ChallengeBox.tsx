"use client";

import { motion } from "framer-motion";
import { MessageCircleQuestion, Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChallengeBoxProps {
  onSubmit: (challengeText: string) => void;
  disabled?: boolean;
}

export function ChallengeBox({ onSubmit, disabled }: ChallengeBoxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [text, setText] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setText("");
    setIsOpen(false);
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        disabled={disabled}
        className="flex w-full items-center gap-3 rounded-xl border border-dashed border-border/70 p-4 text-left text-sm transition-colors hover:border-primary/40 hover:bg-accent/30 disabled:opacity-50"
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-gold/20 text-primary">
          <MessageCircleQuestion className="h-4 w-4" />
        </span>
        <span className="text-muted-foreground">
          <span className="font-medium text-foreground">Something seem off? </span>
          Challenge this verdict or ask TruthOS to re-verify a specific point.
        </span>
      </button>
    );
  }

  return (
    <motion.form
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      onSubmit={handleSubmit}
      className="glass flex flex-col gap-3 rounded-xl border border-primary/30 p-4"
    >
      <label className="flex items-center gap-2 text-sm font-medium">
        <MessageCircleQuestion className="h-4 w-4 text-primary" />
        What seems wrong, unconfirmed, or worth double-checking?
      </label>
      <Textarea
        autoFocus
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={`e.g. "This source looks biased" or "Can you verify the NASA claim specifically?"`}
        className="min-h-20"
      />
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={() => setIsOpen(false)}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={!text.trim() || disabled}>
          Re-verify <Send className="h-3.5 w-3.5" />
        </Button>
      </div>
    </motion.form>
  );
}
