"use client";

import { SendHorizontal } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  onSubmit: (query: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSubmit, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  }

  return (
    <form onSubmit={handleSubmit} className="px-4 pb-5 pt-2">
      <div className="glass shadow-glow flex items-end gap-2 rounded-2xl border border-border/70 p-2 pl-4 transition-colors focus-within:border-primary/50">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              handleSubmit(e);
            }
          }}
          placeholder="Ask TruthOS to investigate something..."
          disabled={disabled}
          className="max-h-40 flex-1 resize-none border-none bg-transparent px-0 py-2 shadow-none focus-visible:ring-0"
        />
        <Button
          type="submit"
          size="icon"
          className="mb-0.5 shrink-0"
          disabled={disabled || !value.trim()}
          aria-label="Send"
        >
          <SendHorizontal className="h-4 w-4" />
        </Button>
      </div>
    </form>
  );
}
