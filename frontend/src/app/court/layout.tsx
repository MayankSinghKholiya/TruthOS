"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CourtSidebar } from "@/components/court/CourtSidebar";
import { useAuthStore } from "@/store/authStore";

export default function CourtLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    setHasHydrated(true);
  }, []);

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace("/login");
    }
  }, [hasHydrated, accessToken, router]);

  if (!hasHydrated || !accessToken) {
    return null;
  }

  return (
    <div className="flex h-screen">
      <CourtSidebar />
      {children}
    </div>
  );
}
