import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { TokenPair, User } from "@/types";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  setSession: (user: User, tokens: TokenPair) => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      setSession: (user, tokens) =>
        set({ user, accessToken: tokens.access_token, refreshToken: tokens.refresh_token }),
      clearSession: () => set({ user: null, accessToken: null, refreshToken: null }),
    }),
    { name: "truthos-auth" },
  ),
);
