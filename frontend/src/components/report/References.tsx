import { Link2 } from "lucide-react";

import type { ReferenceItem } from "@/types";

export function References({ references }: { references: ReferenceItem[] }) {
  if (references.length === 0) {
    return <p className="text-sm text-muted-foreground">No external references were cited.</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {references.map((ref, i) => (
        <li key={i} className="flex items-start gap-2 text-sm">
          <Link2 className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          {ref.url ? (
            <a href={ref.url} target="_blank" rel="noreferrer" className="text-primary underline underline-offset-4">
              {ref.title}
            </a>
          ) : (
            <span>{ref.title}</span>
          )}
          {ref.published_at && (
            <span className="text-xs text-muted-foreground">({ref.published_at.slice(0, 10)})</span>
          )}
        </li>
      ))}
    </ul>
  );
}
