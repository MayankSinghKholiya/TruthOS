import { create } from "zustand";

import type { Dispute, DisputeVerdict } from "@/types";

export interface CourtTraceEntry {
  nodeName: string;
}

interface CourtState {
  disputes: Dispute[];
  currentDispute: Dispute | null;
  currentVerdict: DisputeVerdict | null;
  isArbitrating: boolean;
  trace: CourtTraceEntry[];
  error: string | null;

  setDisputes: (disputes: Dispute[]) => void;
  setCurrentDispute: (dispute: Dispute | null) => void;
  startArbitrating: () => void;
  pushTraceStep: (nodeName: string) => void;
  finishArbitrating: (verdict: DisputeVerdict | null) => void;
  setError: (message: string | null) => void;
  reset: () => void;
}

export const useCourtStore = create<CourtState>()((set) => ({
  disputes: [],
  currentDispute: null,
  currentVerdict: null,
  isArbitrating: false,
  trace: [],
  error: null,

  setDisputes: (disputes) => set({ disputes }),
  setCurrentDispute: (dispute) => set({ currentDispute: dispute }),
  startArbitrating: () => set({ isArbitrating: true, trace: [], currentVerdict: null, error: null }),
  pushTraceStep: (nodeName) =>
    set((state) => ({ trace: [...state.trace, { nodeName }] })),
  finishArbitrating: (verdict) => set({ isArbitrating: false, currentVerdict: verdict }),
  setError: (message) => set({ error: message, isArbitrating: false }),
  reset: () => set({ currentDispute: null, currentVerdict: null, trace: [], error: null }),
}));
