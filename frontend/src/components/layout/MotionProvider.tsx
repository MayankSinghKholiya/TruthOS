"use client";

import { MotionConfig } from "framer-motion";

/** Applies to every motion.* component in the tree without touching each
 * one individually: reducedMotion="user" makes Framer Motion respect the
 * OS-level prefers-reduced-motion setting automatically, disabling
 * transform-driven animation (slides, scales) while still allowing opacity
 * fades - Framer Motion's own accessible default, not a custom rule. */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
