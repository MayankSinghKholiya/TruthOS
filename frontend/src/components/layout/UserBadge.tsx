export function UserBadge({ email }: { email?: string | null }) {
  const initial = email?.trim()?.[0]?.toUpperCase() ?? "?";
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-gold text-xs font-semibold text-white">
        {initial}
      </span>
      <span className="truncate text-sm text-muted-foreground">{email}</span>
    </div>
  );
}
