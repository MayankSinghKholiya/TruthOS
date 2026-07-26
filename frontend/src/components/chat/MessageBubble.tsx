import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-2xl whitespace-pre-wrap rounded-lg px-4 py-2.5 text-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
        )}
      >
        {message.content}
      </div>
    </div>
  );
}
