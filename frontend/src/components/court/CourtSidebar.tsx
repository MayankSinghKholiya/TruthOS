"use client";

import { Bell, Gavel, KeyRound, LogOut, Plus, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Logo } from "@/components/layout/Logo";
import { ProductSwitcher } from "@/components/layout/ProductSwitcher";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { UserBadge } from "@/components/layout/UserBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { courtApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";
import { useCourtStore } from "@/store/courtStore";

const STATUS_VARIANT: Record<string, "success" | "secondary" | "destructive"> = {
  resolved: "success",
  open: "secondary",
  failed: "destructive",
};

export function CourtSidebar() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const clearSession = useAuthStore((s) => s.clearSession);
  const disputes = useCourtStore((s) => s.disputes);
  const currentDispute = useCourtStore((s) => s.currentDispute);
  const setDisputes = useCourtStore((s) => s.setDisputes);

  useEffect(() => {
    courtApi
      .listDisputes()
      .then(setDisputes)
      .catch(() => setDisputes([]));
  }, [setDisputes]);

  function handleNewDispute() {
    useCourtStore.getState().reset();
    router.push("/court/file");
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
        <Button variant="gold" className="w-full justify-start gap-2" onClick={handleNewDispute}>
          <Plus className="h-4 w-4" /> File a dispute
        </Button>
        <Button
          variant="outline"
          className="w-full justify-start gap-2"
          onClick={() => router.push("/court/reputation")}
        >
          <ShieldCheck className="h-4 w-4" /> Check reputation
        </Button>
        <Button
          variant="outline"
          className="w-full justify-start gap-2"
          onClick={() => router.push("/court/api-keys")}
        >
          <KeyRound className="h-4 w-4" /> Agent API keys
        </Button>
        <Button
          variant="outline"
          className="w-full justify-start gap-2"
          onClick={() => router.push("/court/telegram")}
        >
          <Bell className="h-4 w-4" /> Telegram alerts
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3">
        {disputes.length > 0 && (
          <p className="px-2 pb-1.5 pt-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Disputes
          </p>
        )}
        {disputes.length === 0 && (
          <p className="px-2 py-2 text-sm text-muted-foreground">No disputes filed yet.</p>
        )}
        <div className="flex flex-col gap-0.5">
          {disputes.map((dispute) => {
            const isActive = currentDispute?.id === dispute.id;
            return (
              <button
                key={dispute.id}
                onClick={() => router.push(`/court/${dispute.id}`)}
                className={cn(
                  "group relative flex w-full flex-col gap-1.5 rounded-lg px-3 py-2.5 text-left transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-accent/50 hover:text-foreground",
                )}
              >
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-gold" />
                )}
                <div className="flex items-center gap-2.5">
                  <Gavel className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate text-sm">{dispute.task_description}</span>
                </div>
                <Badge
                  variant={STATUS_VARIANT[dispute.status] ?? "secondary"}
                  className="ml-[1.625rem] w-fit capitalize"
                >
                  {dispute.status}
                </Badge>
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
