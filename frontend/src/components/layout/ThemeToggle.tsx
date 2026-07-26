"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

export const THEME_STORAGE_KEY = "truthos-theme";

function getStoredTheme(): "light" | "dark" | null {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "light" || stored === "dark" ? stored : null;
}

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Explicit light/dark toggle. The CSS already supports three states -
 * unset (follow system), data-theme="dark", data-theme="light" - this
 * only ever writes an explicit choice; the inline script in layout.tsx
 * applies a previously-stored choice before first paint so there's no
 * flash of the wrong theme on load. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setTheme(getStoredTheme() ?? (systemPrefersDark() ? "dark" : "light"));
    setMounted(true);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(THEME_STORAGE_KEY, next);
  }

  if (!mounted) return <div className="h-10 w-10" aria-hidden />;

  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
      {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}
