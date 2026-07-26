"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthShell } from "@/components/layout/AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, authApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

export default function LoginPage() {
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const tokens = await authApi.login(email, password);
      useAuthStore.setState({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
      const user = await authApi.me();
      setSession(user, tokens);
      router.push("/chat");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <div className="mb-8 flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-medium tracking-tight">Welcome back</h1>
        <p className="text-sm text-muted-foreground">
          Sign in to access your investigations and evidence trail.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" size="lg" className="mt-2" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Sign in"} <ArrowRight className="h-4 w-4" />
        </Button>
        <p className="text-center text-sm text-muted-foreground">
          No account?{" "}
          <a href="/register" className="font-medium text-primary underline underline-offset-4">
            Register
          </a>
        </p>
      </form>
    </AuthShell>
  );
}
