"use client";

import { LogOut, Plus, ScrollText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Logo } from "@/components/layout/Logo";
import { ProductSwitcher } from "@/components/layout/ProductSwitcher";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { UserBadge } from "@/components/layout/UserBadge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { chatApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { useChatStore } from "@/store/chatStore";

export function Sidebar() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const clearSession = useAuthStore((s) => s.clearSession);
  const sessions = useChatStore((s) => s.sessions);
  const currentSessionId = useChatStore((s) => s.currentSessionId);
  const setSessions = useChatStore((s) => s.setSessions);

  useEffect(() => {
    chatApi
      .listSessions()
      .then(setSessions)
      .catch(() => setSessions([]));
  }, [setSessions]);

  function handleNewInvestigation() {
    useChatStore.getState().reset();
    useChatStore.getState().setCurrentSessionId(null);
    router.push("/chat");
  }

  function handleLogout() {
    clearSession();
    router.push("/login");
  }

  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col border-r border-border/70 bg-muted/20">
      <div className="flex flex-col gap-4 p-4">
        <div className="px-1 pb-1">
          <Logo size={30} />
        </div>
        <ProductSwitcher />
        <Button className="w-full justify-start gap-2" onClick={handleNewInvestigation}>
          <Plus className="h-4 w-4" /> New investigation
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3">
        {sessions.length > 0 && (
          <p className="px-2 pb-1.5 pt-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Investigations
          </p>
        )}
        <div className="flex flex-col gap-0.5">
          {sessions.map((session) => {
            const isActive = currentSessionId === session.id;
            return (
              <button
                key={session.id}
                onClick={() => router.push(`/chat/${session.id}`)}
                className={cn(
                  "group relative flex w-full items-center gap-2.5 truncate rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
                )}
                <ScrollText className="h-4 w-4 shrink-0 opacity-70" />
                <span className="truncate">{session.title}</span>
              </button>
            );
          })}
        </div>
      </nav>

      <div className="flex items-center justify-between border-t border-border/70 p-4">
        <UserBadge email={user?.email} />
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <Button variant="ghost" size="icon" onClick={handleLogout} aria-label="Log out">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </aside>
  );
}
