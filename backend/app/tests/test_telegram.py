import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.telegram_bot import TelegramBotService
from app.services.telegram_linking import _START_PATTERN, generate_link_code
from app.services.telegram_notify import (
    _extract_tx_references,
    _message,
    _owners_for_wallet,
    _tx_field,
    wallet_history_summary,
)


def test_start_pattern_matches_valid_code():
    match = _START_PATTERN.match("/start 482913")
    assert match is not None
    assert match.group(1) == "482913"


def test_start_pattern_rejects_wrong_length_code():
    assert _START_PATTERN.match("/start 4829") is None
    assert _START_PATTERN.match("/start 48291399") is None


def test_start_pattern_rejects_other_commands():
    assert _START_PATTERN.match("/help") is None
    assert _START_PATTERN.match("just some text") is None


async def test_generate_link_code_is_six_digits_and_stored_in_redis():
    redis = AsyncMock()
    user_id = uuid.uuid4()

    code = await generate_link_code(redis, user_id)

    assert len(code) == 6
    assert code.isdigit()
    redis.set.assert_awaited_once()
    args, kwargs = redis.set.call_args
    assert args[0] == f"telegram_link_code:{code}"
    assert args[1] == str(user_id)
    assert kwargs["ex"] == 600


def test_extract_tx_references_pulls_chain_and_hash():
    evidence = [
        {"chain": "base", "verification_details": {"tx_hash": "0xabc123"}},
        {"verification_details": None},
        {"verification_details": {"other_field": "x"}},
    ]
    assert _extract_tx_references(evidence) == [("base", "0xabc123")]


def test_extract_tx_references_empty_when_none_present():
    assert _extract_tx_references([{"verification_details": {}}]) == []


def test_tx_field_none_with_no_references():
    assert _tx_field([]) is None


def test_tx_field_includes_chain_name_when_present():
    evidence = [{"chain": "base", "verification_details": {"tx_hash": "0xabc123"}}]
    label, value = _tx_field(evidence)
    assert "0xabc123" in value
    assert "(base)" in label


def test_tx_field_omits_chain_label_when_chain_unknown():
    evidence = [{"verification_details": {"tx_hash": "0xabc123"}}]
    label, value = _tx_field(evidence)
    assert "0xabc123" in value
    assert "(" not in label


def test_bot_service_not_configured_without_token():
    service = TelegramBotService(http_client=MagicMock(), bot_token="")
    assert service.is_configured is False


async def test_bot_service_send_message_noop_when_not_configured():
    http_client = AsyncMock()
    service = TelegramBotService(http_client=http_client, bot_token="")

    result = await service.send_message("12345", "hello")

    assert result is False
    http_client.post.assert_not_called()


async def test_bot_service_send_message_returns_true_on_success():
    http_client = AsyncMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    http_client.post.return_value = response
    service = TelegramBotService(http_client=http_client, bot_token="fake-token")

    result = await service.send_message("12345", "hello")

    assert result is True
    http_client.post.assert_awaited_once()


async def test_bot_service_send_message_returns_false_on_http_error():
    import httpx

    http_client = AsyncMock()
    http_client.post.side_effect = httpx.ConnectTimeout("timed out")
    service = TelegramBotService(http_client=http_client, bot_token="fake-token")

    result = await service.send_message("12345", "hello")

    assert result is False


def _link(chat_id: str) -> MagicMock:
    return MagicMock(telegram_chat_id=chat_id)


async def test_owners_for_wallet_dedupes_watch_and_api_key_owner():
    # Same chat_id shows up via both an explicit watch AND an API-key owner
    # lookup - must only appear once in the result.
    session = AsyncMock()
    watch_result = MagicMock()
    watch_result.scalars.return_value.all.return_value = [_link("777"), _link("888")]
    api_key_result = MagicMock()
    api_key_result.scalars.return_value.all.return_value = [_link("888")]  # overlaps
    session.execute = AsyncMock(side_effect=[watch_result, api_key_result])

    chat_ids = await _owners_for_wallet(session, "0xSomeWallet")

    assert set(chat_ids) == {"777", "888"}
    assert len(chat_ids) == 2


async def test_owners_for_wallet_empty_when_no_watch_or_key():
    session = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(side_effect=[empty_result, empty_result])

    chat_ids = await _owners_for_wallet(session, "0xUnrelated")

    assert chat_ids == []


def _reputation(total: int, at_fault: int) -> MagicMock:
    return MagicMock(disputes_total=total, disputes_at_fault=at_fault)


async def _summary_session(reputation, open_count: int) -> AsyncMock:
    session = AsyncMock()
    rep_result = MagicMock()
    rep_result.scalar_one_or_none = MagicMock(return_value=reputation)
    count_result = MagicMock()
    count_result.scalar_one = MagicMock(return_value=open_count)
    session.execute = AsyncMock(side_effect=[rep_result, count_result])
    return session


async def test_wallet_history_summary_no_history():
    session = await _summary_session(None, 0)
    assert await wallet_history_summary(session, "0xFresh") == "No prior dispute history"


async def test_wallet_history_summary_with_disputes_and_at_fault():
    session = await _summary_session(_reputation(total=5, at_fault=2), 0)
    assert await wallet_history_summary(session, "0xWallet") == "5 prior disputes, 2 at fault"


async def test_wallet_history_summary_singular_for_one_dispute():
    session = await _summary_session(_reputation(total=1, at_fault=0), 0)
    assert await wallet_history_summary(session, "0xWallet") == "1 prior dispute"


async def test_wallet_history_summary_includes_currently_open():
    session = await _summary_session(_reputation(total=3, at_fault=0), 1)
    summary = await wallet_history_summary(session, "0xWallet")
    assert "3 prior disputes" in summary
    assert "1 currently open/unresolved" in summary


def test_message_puts_a_blank_line_between_sections():
    # Regression test: an earlier version built blank-line spacers into the
    # parts list, then filtered out every empty string before joining -
    # which silently deleted the very spacing it was trying to add.
    text = _message(
        emoji="\U0001f6a8",
        headline="Headline",
        intro="Intro sentence.",
        when="2026-01-01 00:00 UTC",
        fields=[("Field", "Value")],
        footer="Footer note.",
    )
    lines = text.split("\n")
    assert "" in lines  # at least one genuine blank line survived
    assert "Intro sentence." in lines
    assert "Footer note." in lines
    # the details block itself stays tight - no blank line between the
    # timestamp and the field line
    details_index = lines.index("\U0001f4c5 2026-01-01 00:00 UTC")
    assert lines[details_index + 1] == "Field: Value"


def test_message_without_footer_has_no_trailing_section():
    text = _message(
        emoji="⚠️", headline="H", intro="I", when="W", fields=[("F", "V")]
    )
    assert not text.endswith("\n\n")
