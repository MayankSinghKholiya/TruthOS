import { create } from "zustand";

import type { ChatMessage, ChatSession, LayeredReport } from "@/types";

export interface AgentTraceEntry {
  agentName: string;
  status: "running" | "completed";
}

interface ChatState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  agentTrace: AgentTraceEntry[];
  error: string | null;

  setSessions: (sessions: ChatSession[]) => void;
  setCurrentSessionId: (id: string | null) => void;
  setMessages: (messages: ChatMessage[]) => void;
  appendUserMessage: (content: string) => void;
  startStreaming: () => void;
  pushAgentStep: (agentName: string) => void;
  finishStreaming: (report: LayeredReport | null) => void;
  setError: (message: string | null) => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>()((set) => ({
  sessions: [],
  currentSessionId: null,
  messages: [],
  isStreaming: false,
  agentTrace: [],
  error: null,

  setSessions: (sessions) => set({ sessions }),
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  setMessages: (messages) => set({ messages }),
  appendUserMessage: (content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: crypto.randomUUID(),
          role: "user",
          content,
          created_at: new Date().toISOString(),
        },
      ],
    })),
  startStreaming: () => set({ isStreaming: true, agentTrace: [], error: null }),
  pushAgentStep: (agentName) =>
    set((state) => ({
      agentTrace: [...state.agentTrace, { agentName, status: "completed" }],
    })),
  // Each finished report is attached to its own assistant message, rather
  // than kept in one shared "current report" slot - otherwise every new
  // query's report would overwrite and hide the previous one's full view.
  finishStreaming: (report) =>
    set((state) => ({
      isStreaming: false,
      messages: report
        ? [
            ...state.messages,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: report.executive_summary,
              created_at: new Date().toISOString(),
              report,
            },
          ]
        : state.messages,
    })),
  setError: (message) => set({ error: message, isStreaming: false }),
  reset: () => set({ messages: [], agentTrace: [], error: null }),
}));
