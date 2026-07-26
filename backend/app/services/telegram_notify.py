"""Telegram notification triggers for TruthOS Court:

  1. notify_dispute_filed          - a dispute was just filed against a
                                      wallet someone owns or is watching.
  2. notify_flagged_counterparty   - a just-resolved verdict left one party
                                      Flagged, and the other party is owned
                                      or watched.
  3. notify_interaction_with_flagged - fires at FILING time, not verdict
                                      time: if either party was *already*
                                      Flagged before this dispute even
                                      started, the other party's owner gets
                                      warned immediately - the "you should
                                      have checked first" alert.

"Owned or watched" - see _owners_for_wallet: a wallet's Telegram audience is
anyone who explicitly registered a watch on it, PLUS anyone holding an API
key minted for it (filing a dispute with that key already proves it's
theirs, without needing a separate watch).

Every message shares one format (_message): a headline, a UTC timestamp, the
wallet(s) involved, a dispute-history summary (total / at-fault / currently
open - not just a bare trust score), and the on-chain reference with its
chain name when the evidence includes one. A number alone doesn't tell
anyone what actually happened; this is meant to read like an incident
report, not a bare alert.

All triggers are side effects of an already-committed database change - a
failed Telegram delivery must never undo or block the dispute/verdict
itself, which is why TelegramBotService.send_message swallows its own
errors.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.api_key import ApiKey
from app.db.models.dispute import AgentReputation, Dispute, DisputeVerdict
from app.db.models.telegram import TelegramLink, WalletWatch
from app.services.reputation import DEFAULT_TRUST_SCORE, standing_label
from app.services.telegram_bot import TelegramBotService


async def _owners_for_wallet(session: AsyncSession, wallet_id: str) -> list[str]:
    """Telegram chat_ids to notify about activity on this wallet: explicit
    watchers, plus (deduped) anyone whose API key was minted for it."""
    watch_result = await session.execute(
        select(TelegramLink)
        .join(WalletWatch, WalletWatch.user_id == TelegramLink.user_id)
        .where(WalletWatch.wallet_id == wallet_id)
    )
    api_key_result = await session.execute(
        select(TelegramLink)
        .join(ApiKey, ApiKey.created_by_user_id == TelegramLink.user_id)
        .where(ApiKey.wallet_id == wallet_id, ApiKey.revoked_at.is_(None))
    )
    chat_ids = {link.telegram_chat_id for link in watch_result.scalars().all()}
    chat_ids.update(link.telegram_chat_id for link in api_key_result.scalars().all())
    return list(chat_ids)


async def wallet_history_summary(session: AsyncSession, wallet_id: str) -> str:
    """"Prior allegations" in one line: total disputes, how many at fault,
    and - distinct from either - how many are still open right now. A bare
    trust score doesn't say whether there's an unresolved dispute sitting
    against this wallet at this very moment; this does."""
    rep_result = await session.execute(select(AgentReputation).where(AgentReputation.wallet_id == wallet_id))
    reputation = rep_result.scalar_one_or_none()
    total = reputation.disputes_total if reputation else 0
    at_fault = reputation.disputes_at_fault if reputation else 0

    open_result = await session.execute(
        select(func.count())
        .select_from(Dispute)
        .where(
            or_(Dispute.claimant_wallet_id == wallet_id, Dispute.respondent_wallet_id == wallet_id),
            Dispute.status == "open",
        )
    )
    open_count = open_result.scalar_one()

    if total == 0 and open_count == 0:
        return "No prior dispute history"

    parts = [f"{total} prior dispute{'s' if total != 1 else ''}"]
    if at_fault:
        parts.append(f"{at_fault} at fault")
    if open_count:
        parts.append(f"{open_count} currently open/unresolved")
    return ", ".join(parts)


def _extract_tx_references(evidence: list[dict[str, Any]]) -> list[tuple[str | None, str]]:
    """Returns (chain, tx_hash) pairs for every tx_reference evidence item
    that was actually checked against a chain."""
    refs = []
    for item in evidence:
        details = item.get("verification_details") or {}
        tx_hash = details.get("tx_hash")
        if tx_hash:
            refs.append((item.get("chain") or details.get("chain"), tx_hash))
    return refs


def _format_when(moment: datetime | None) -> str:
    if moment is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _tx_field(evidence: list[dict[str, Any]]) -> tuple[str, str] | None:
    """A (label, value) field for the first tx_reference evidence item that
    was actually checked against a chain - same shape as every other field,
    so callers just splice it into their `fields` list wherever it belongs
    (right before the Dispute ID, by convention)."""
    refs = _extract_tx_references(evidence)
    if not refs:
        return None
    chain, tx_hash = refs[0]
    label = f"\U0001f517 Transaction ({chain})" if chain else "\U0001f517 Transaction"
    return label, f"<code>{tx_hash}</code>"


def _message(
    *,
    emoji: str,
    headline: str,
    intro: str,
    when: str,
    fields: list[tuple[str, str]],
    footer: str = "",
) -> str:
    """Joins logical sections (headline / intro / details block / footer)
    with a blank line between each, so the message actually reads as
    structured paragraphs in Telegram rather than one run-on block - each
    section's own lines stay tight (single newline), only the boundaries
    between sections get the extra spacing."""
    detail_lines = [f"\U0001f4c5 {when}"] + [f"{label}: {value}" for label, value in fields]
    sections = [f"{emoji} <b>{headline}</b>", intro, "\n".join(detail_lines)]
    if footer:
        sections.append(footer)
    return "\n\n".join(sections)


async def notify_dispute_filed(
    session: AsyncSession, bot: TelegramBotService, dispute: Dispute, evidence: list[dict[str, Any]]
) -> None:
    if not bot.is_configured:
        return
    chat_ids = await _owners_for_wallet(session, dispute.respondent_wallet_id)
    if not chat_ids:
        return

    history = await wallet_history_summary(session, dispute.respondent_wallet_id)
    fields = [
        ("\U0001f45b Respondent (watched)", f"<code>{dispute.respondent_wallet_id}</code>"),
        ("\U0001f45b Claimant", f"<code>{dispute.claimant_wallet_id}</code>"),
        ("\U0001f4ca Respondent history", history),
        ("\U0001f4dd Task", dispute.task_description),
    ]
    tx_field = _tx_field(evidence)
    if tx_field:
        fields.append(tx_field)
    fields.append(("\U0001f194 Dispute ID", f"<code>{dispute.id}</code>"))

    message = _message(
        emoji="⚠️",
        headline="New Dispute Filed",
        intro="A dispute has just been filed against a wallet you're watching.",
        when=_format_when(dispute.created_at),
        fields=fields,
    )
    for chat_id in chat_ids:
        await bot.send_message(chat_id, message)


async def notify_flagged_counterparty(
    session: AsyncSession,
    bot: TelegramBotService,
    dispute: Dispute,
    verdict: DisputeVerdict,
    evidence: list[dict[str, Any]],
    claimant_trust_score: float,
    respondent_trust_score: float,
) -> None:
    if not bot.is_configured:
        return

    when = _format_when(verdict.created_at)
    pairs = [
        (dispute.claimant_wallet_id, dispute.respondent_wallet_id, claimant_trust_score),
        (dispute.respondent_wallet_id, dispute.claimant_wallet_id, respondent_trust_score),
    ]
    for flagged_wallet, counterparty_wallet, trust_score in pairs:
        if standing_label(trust_score) != "Flagged":
            continue
        chat_ids = await _owners_for_wallet(session, counterparty_wallet)
        if not chat_ids:
            continue

        history = await wallet_history_summary(session, flagged_wallet)
        fields = [
            ("\U0001f45b Your wallet", f"<code>{counterparty_wallet}</code>"),
            ("\U0001f45b Flagged counterparty", f"<code>{flagged_wallet}</code>"),
            ("\U0001f4ca Counterparty history", f"{history} (trust score {trust_score:.0f}/100)"),
            ("⚖️ Verdict", verdict.verdict),
        ]
        tx_field = _tx_field(evidence)
        if tx_field:
            fields.append(tx_field)
        fields.append(("\U0001f194 Dispute ID", f"<code>{dispute.id}</code>"))

        message = _message(
            emoji="\U0001f6a9",
            headline="Counterparty Now Flagged",
            intro="A dispute you were party to just resolved, and the other side is now Flagged.",
            when=when,
            fields=fields,
        )
        for chat_id in chat_ids:
            await bot.send_message(chat_id, message)


async def notify_interaction_with_flagged(
    session: AsyncSession, bot: TelegramBotService, dispute: Dispute, evidence: list[dict[str, Any]]
) -> None:
    """Fires at filing time: the dispute's existence already proves an
    interaction happened, regardless of whether anyone ran a safety check
    first. If either party was ALREADY Flagged (from disputes resolved
    before this one), the other party's owner is warned immediately - not
    just at verdict time, and not only if they'd set up a watch."""
    if not bot.is_configured:
        return

    rep_result = await session.execute(
        select(AgentReputation).where(
            AgentReputation.wallet_id.in_([dispute.claimant_wallet_id, dispute.respondent_wallet_id])
        )
    )
    scores = {rep.wallet_id: rep.trust_score for rep in rep_result.scalars().all()}

    pairs = [
        (dispute.claimant_wallet_id, dispute.respondent_wallet_id),
        (dispute.respondent_wallet_id, dispute.claimant_wallet_id),
    ]
    for flagged_wallet, counterparty_wallet in pairs:
        score = scores.get(flagged_wallet, DEFAULT_TRUST_SCORE)
        if standing_label(score) != "Flagged":
            continue
        chat_ids = await _owners_for_wallet(session, counterparty_wallet)
        if not chat_ids:
            continue

        history = await wallet_history_summary(session, flagged_wallet)
        fields = [
            ("\U0001f45b Your wallet", f"<code>{counterparty_wallet}</code>"),
            ("\U0001f45b Flagged counterparty", f"<code>{flagged_wallet}</code>"),
            ("\U0001f4ca Counterparty history", f"{history} (trust score {score:.0f}/100)"),
            ("\U0001f4dd Task", dispute.task_description),
        ]
        tx_field = _tx_field(evidence)
        if tx_field:
            fields.append(tx_field)
        fields.append(("\U0001f194 Dispute ID", f"<code>{dispute.id}</code>"))

        message = _message(
            emoji="\U0001f6a8",
            headline="Interaction With a Flagged Wallet",
            intro="You interacted with a wallet that was already Flagged - no safety check appears to have been run first.",
            when=_format_when(dispute.created_at),
            fields=fields,
            footer="Tip: run a reputation check before engaging next time.",
        )
        for chat_id in chat_ids:
            await bot.send_message(chat_id, message)
