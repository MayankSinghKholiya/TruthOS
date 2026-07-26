import uuid

from app.api.v1.disputes import _resolve_claimant_wallet_id
from app.db.models.api_key import ApiKey
from app.schemas.dispute import AgentDisputeCreate


def _api_key(*, is_bridge: bool, wallet_id: str = "0xkeywallet") -> ApiKey:
    return ApiKey(
        created_by_user_id=uuid.uuid4(),
        wallet_id=wallet_id,
        key_hash="hash",
        key_prefix="tos_abc123",
        is_bridge=is_bridge,
    )


def _payload(**overrides) -> AgentDisputeCreate:
    defaults = dict(
        respondent_wallet_id="0xrespondent",
        task_description="task",
        agreed_deliverable="agreed",
        actual_deliverable="actual",
    )
    defaults.update(overrides)
    return AgentDisputeCreate(**defaults)


def test_regular_key_always_files_as_its_own_wallet():
    api_key = _api_key(is_bridge=False, wallet_id="0xagent")
    payload = _payload(claimant_wallet_id="0xsomeone_else")
    assert _resolve_claimant_wallet_id(api_key, payload) == "0xagent"


def test_regular_key_ignores_missing_claimant_and_uses_own_wallet():
    api_key = _api_key(is_bridge=False, wallet_id="0xagent")
    payload = _payload()
    assert _resolve_claimant_wallet_id(api_key, payload) == "0xagent"


def test_bridge_key_uses_explicit_claimant_from_payload():
    api_key = _api_key(is_bridge=True, wallet_id="0xbridge")
    payload = _payload(claimant_wallet_id="0xclaimant_party")
    assert _resolve_claimant_wallet_id(api_key, payload) == "0xclaimant_party"


def test_bridge_key_falls_back_to_own_wallet_when_claimant_unset():
    api_key = _api_key(is_bridge=True, wallet_id="0xbridge")
    payload = _payload()
    assert _resolve_claimant_wallet_id(api_key, payload) == "0xbridge"


def test_bridge_key_falls_back_to_own_wallet_when_claimant_empty_string():
    api_key = _api_key(is_bridge=True, wallet_id="0xbridge")
    payload = _payload(claimant_wallet_id="")
    assert _resolve_claimant_wallet_id(api_key, payload) == "0xbridge"
