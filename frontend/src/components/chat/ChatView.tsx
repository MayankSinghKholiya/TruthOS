"use client";

import { useEffect, useRef } from "react";

import { AgentTraceIndicator } from "@/components/chat/AgentTraceIndicator";
import { ChatEmptyState } from "@/components/chat/ChatEmptyState";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { LayeredReportView } from "@/components/report/LayeredReportView";
import { chatApi, reportsApi, streamQuery } from "@/lib/api";
import { composeChallengeQuery } from "@/lib/challenge";
import { useChatStore } from "@/store/chatStore";
import type { LayeredReport, StreamEvent } from "@/types";

export function ChatView({ sessionId }: { sessionId?: string }) {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const agentTrace = useChatStore((s) => s.agentTrace);
  const error = useChatStore((s) => s.error);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    useChatStore.getState().setCurrentSessionId(sessionId ?? null);
    if (!sessionId) {
      useChatStore.getState().reset();
      return;
    }
    useChatStore.getState().reset();
    Promise.all([chatApi.getMessages(sessionId), reportsApi.getBySession(sessionId)])
      .then(([msgs, reports]) => {
        const reportsById = new Map(reports.filter((r) => r.id).map((r) => [r.id as string, r]));
        const hydrated = msgs.map((msg) => {
          const reportId = msg.meta?.report_id;
          const report = reportId ? reportsById.get(reportId) : undefined;
          return report ? { ...msg, report } : msg;
        });
        useChatStore.getState().setMessages(hydrated);
      })
      .catch(() => undefined);
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, agentTrace]);

  async function handleSubmit(query: string) {
    const store = useChatStore.getState();
    store.appendUserMessage(query);
    store.startStreaming();

    try {
      await streamQuery(query, sessionId ?? null, (event: StreamEvent) => {
        if (event.type === "agent_completed" && event.agent_name) {
          useChatStore.getState().pushAgentStep(event.agent_name);
        }
        if (event.type === "report_ready") {
          useChatStore.getState().finishStreaming(event.data as unknown as LayeredReport);
        }
        if (event.type === "error") {
          useChatStore.getState().setError((event.data.message as string) ?? "Something went wrong");
        }
      });
    } catch {
      useChatStore.getState().setError("Failed to reach TruthOS. Is the backend running?");
    }
  }

  const isEmpty = messages.length === 0 && !isStreaming;

  return (
    <div className="flex h-screen flex-1 flex-col">
      <div className={`flex-1 overflow-y-auto ${isEmpty ? "flex flex-col" : ""}`}>
        <div className={`mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-6 py-8`}>
          {isEmpty && <ChatEmptyState onSuggestion={handleSubmit} />}

          {messages.map((message) =>
            message.role === "assistant" && message.report ? (
              <LayeredReportView
                key={message.id}
                report={message.report}
                isBusy={isStreaming}
                onChallenge={(challengeText) =>
                  handleSubmit(composeChallengeQuery(message.report!, challengeText))
                }
              />
            ) : (
              <MessageBubble key={message.id} message={message} />
            ),
          )}

          {isStreaming && <AgentTraceIndicator trace={agentTrace} />}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div ref={scrollRef} />
        </div>
      </div>

      <div className="mx-auto w-full max-w-3xl">
        <ChatInput onSubmit={handleSubmit} disabled={isStreaming} />
      </div>
    </div>
  );
}
