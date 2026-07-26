import Image from "next/image";
import Link from "next/link";

import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  iconOnly?: boolean;
  size?: number;
  /** Set false for decorative/non-navigational uses (e.g. a centerpiece
   * icon in an empty state) - every other placement (sidebars, auth panels,
   * the landing page's own header) should take you back to the marketing
   * landing page. */
  linkToHome?: boolean;
}

function LogoMark({ className, iconOnly = false, size = 36 }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Image
        src="/logo.png"
        alt="TruthOS"
        width={size}
        height={size}
        priority
        className="shrink-0 rounded-[28%] shadow-sm ring-1 ring-black/10"
        style={{ width: size, height: size }}
      />
      {!iconOnly && (
        <span className="font-display text-lg font-semibold tracking-tight">TruthOS</span>
      )}
    </span>
  );
}

/** Brand mark. Links back to the marketing landing page by default. */
export function Logo({ linkToHome = true, ...props }: LogoProps) {
  if (!linkToHome) return <LogoMark {...props} />;
  return (
    <Link href="/" className="transition-opacity hover:opacity-80" aria-label="TruthOS home">
      <LogoMark {...props} />
    </Link>
  );
}
