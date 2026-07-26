"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const PRODUCTS = [
  { href: "/chat", label: "Chat" },
  { href: "/court", label: "Court" },
];

export function ProductSwitcher() {
  const pathname = usePathname();
  return (
    <div className="flex gap-1 rounded-md bg-muted p-1">
      {PRODUCTS.map((product) => {
        const active = pathname?.startsWith(product.href);
        return (
          <Link
            key={product.href}
            href={product.href}
            className={cn(
              "flex-1 rounded-sm px-3 py-1.5 text-center text-sm font-medium transition-colors",
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {product.label}
          </Link>
        );
      })}
    </div>
  );
}
