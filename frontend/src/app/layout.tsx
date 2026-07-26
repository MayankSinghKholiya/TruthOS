import type { Metadata } from "next";
import { Fraunces, Inter } from "next/font/google";

import { MotionProvider } from "@/components/layout/MotionProvider";

import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600"],
  style: ["normal", "italic"],
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const SITE_DESCRIPTION =
  "TruthOS plans, researches, verifies, debates and explains every important answer - separating fact from opinion. TruthOS Court adds an AI arbitrator for agent-to-agent disputes, callable by humans and autonomous agents alike.";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"),
  title: {
    default: "TruthOS - Evidence-Driven Multi-Agent Intelligence",
    template: "%s - TruthOS",
  },
  description: SITE_DESCRIPTION,
  openGraph: {
    title: "TruthOS - Evidence-Driven Multi-Agent Intelligence",
    description: SITE_DESCRIPTION,
    siteName: "TruthOS",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "TruthOS - Evidence-Driven Multi-Agent Intelligence",
    description: SITE_DESCRIPTION,
  },
};

// Keep this key literal in sync with THEME_STORAGE_KEY in ThemeToggle.tsx.
// Runs before first paint (blocking, in <head>) so a stored theme choice
// never flashes the wrong theme for a frame on load.
const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem('truthos-theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${inter.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-background font-sans antialiased">
        <MotionProvider>{children}</MotionProvider>
      </body>
    </html>
  );
}
