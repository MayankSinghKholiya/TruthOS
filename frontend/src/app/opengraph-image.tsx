import { readFile } from "node:fs/promises";
import path from "node:path";

import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "TruthOS - Evidence-Driven Multi-Agent Intelligence Platform";

const CHIPS = ["16 specialist agents", "On-chain verified evidence", "Human + Agent API"];

export default async function OpengraphImage() {
  const logoBuffer = await readFile(path.join(process.cwd(), "public/logo.png"));
  const logoSrc = `data:image/png;base64,${logoBuffer.toString("base64")}`;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          background: "linear-gradient(135deg, #0d0b16 0%, #1c1533 48%, #100c1c 100%)",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <img src={logoSrc} width={72} height={72} style={{ borderRadius: 20 }} alt="" />
          <span style={{ fontSize: 34, fontWeight: 700, color: "#f5f3ff", letterSpacing: -0.5 }}>
            TruthOS
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 980 }}>
          <span
            style={{
              fontSize: 60,
              fontWeight: 700,
              lineHeight: 1.15,
              color: "#f5f3ff",
              letterSpacing: -1,
            }}
          >
            Build the most trustworthy AI,
          </span>
          <span
            style={{
              fontSize: 60,
              fontWeight: 700,
              lineHeight: 1.15,
              letterSpacing: -1,
              background: "linear-gradient(90deg, #a78bfa 0%, #e8c874 100%)",
              backgroundClip: "text",
              color: "transparent",
            }}
          >
            not the fastest one.
          </span>
        </div>

        <div style={{ display: "flex", gap: 14 }}>
          {CHIPS.map((chip) => (
            <div
              key={chip}
              style={{
                display: "flex",
                alignItems: "center",
                padding: "10px 20px",
                borderRadius: 999,
                fontSize: 20,
                color: "#cfc9e8",
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.12)",
              }}
            >
              {chip}
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size },
  );
}
