import { Logo } from "@/components/layout/Logo";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-mesh p-10 lg:flex">
        <div className="bg-grain absolute inset-0" />
        <div className="relative z-10">
          <Logo />
        </div>
        <blockquote className="relative z-10 max-w-md font-display text-3xl font-medium leading-snug">
          Separating fact from opinion,{" "}
          <span className="text-gradient italic">one verdict at a time.</span>
        </blockquote>
        <p className="relative z-10 text-sm text-muted-foreground">
          Evidence-Driven Multi-Agent Intelligence Platform
        </p>
      </div>

      <div className="relative flex w-full flex-col items-center justify-center bg-background px-6 py-16 lg:w-1/2">
        <div className="absolute right-6 top-6">
          <ThemeToggle />
        </div>
        <div className="w-full max-w-sm">
          <div className="mb-10 flex items-center justify-between lg:hidden">
            <Logo />
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
