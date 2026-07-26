import Image from "next/image";

const SAMPLE_LINES: { text: string; bold?: boolean }[] = [
  { text: "🚨 Interaction With a Flagged Wallet", bold: true },
  { text: "" },
  { text: "You interacted with a wallet that was already Flagged - no safety check appears to have been run first." },
  { text: "" },
  { text: "📅 2026-07-26 08:30 UTC" },
  { text: "👛 Your wallet: 0xMyAgentWallet" },
  { text: "👛 Flagged counterparty: 0xShadyWallet" },
  { text: "📊 Counterparty history: 4 prior disputes, 3 at fault, 1 currently open/unresolved (trust score 22/100)" },
  { text: "📝 Task: Logo design task, 250 USDC escrow" },
  { text: "🔗 Transaction (base): 0xdeadbeef...deadbeef" },
  { text: "🆔 Dispute ID: a1b2c3d4-e5f6-7890" },
  { text: "" },
  { text: "Tip: run a reputation check before engaging next time." },
];

/** A styled reproduction of a real message app.services.telegram_notify
 * actually sends - not a mockup invented for marketing, the literal output
 * of _message() with sample data (see the "Interaction With a Flagged
 * Wallet" trigger). */
export function TelegramPreview() {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#0e1621] shadow-2xl">
      <div className="flex items-center gap-3 border-b border-white/10 bg-[#17212b] px-4 py-3">
        <Image src="/logo.png" alt="" width={36} height={36} className="rounded-full" />
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-white">TruthOS Alerts</span>
          <span className="text-xs text-white/40">bot</span>
        </div>
      </div>
      <div className="flex flex-col gap-2 p-4">
        <div className="max-w-[92%] rounded-2xl rounded-tl-sm bg-[#182533] px-4 py-3 text-left">
          {SAMPLE_LINES.map((line, i) =>
            line.text === "" ? (
              <div key={i} className="h-2.5" />
            ) : (
              <p
                key={i}
                className={`text-[13px] leading-relaxed ${
                  line.bold ? "font-semibold text-white" : "text-white/85"
                }`}
              >
                {line.text}
              </p>
            ),
          )}
          <span className="mt-1.5 block text-right text-[11px] text-white/35">08:30</span>
        </div>
      </div>
    </div>
  );
}
