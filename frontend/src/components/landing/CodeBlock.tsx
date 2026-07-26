export function CodeBlock({ label, code }: { label: string; code: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-[#0b0d17] shadow-2xl">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-destructive/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-success/70" />
        <span className="ml-2 font-mono text-[11px] text-white/40">{label}</span>
      </div>
      <pre className="overflow-x-auto p-4 text-left font-mono text-[12.5px] leading-relaxed text-white/80 sm:text-[13px]">
        <code>{code}</code>
      </pre>
    </div>
  );
}
