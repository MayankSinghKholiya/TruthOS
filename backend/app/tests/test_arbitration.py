from app.agents.arbitrator import ArbitratorAgent
from app.agents.claimant import ClaimantAgent
from app.agents.dispute_utils import evidence_needing_forced_discrepancy, format_dispute_evidence
from app.agents.evidence_verifier import EvidenceVerifierAgent
from app.db.models.dispute import AgentReputation
from app.graph.arbitration_orchestrator import _apply_chain_verification_safety_net, _normalize_fault_split
from app.schemas.agent import AgentStatus
from app.services.confidence import compute_arbitration_confidence
from app.services.reputation import apply_dispute_outcome, standing_label


def test_normalize_fault_split_passes_through_valid_split():
    claimant, respondent = _normalize_fault_split(20.0, 80.0)
    assert claimant == 20.0
    assert respondent == 80.0


def test_normalize_fault_split_renormalizes_when_not_summing_to_100():
    # LLM returned two independent guesses that don't add up to 100.
    claimant, respondent = _normalize_fault_split(30.0, 90.0)
    assert round(claimant + respondent, 6) == 100.0
    assert claimant == 25.0  # 30 / 120 * 100
    assert respondent == 75.0


def test_normalize_fault_split_clamps_out_of_range_values():
    claimant, respondent = _normalize_fault_split(150.0, -20.0)
    assert round(claimant + respondent, 6) == 100.0
    assert 0.0 <= claimant <= 100.0
    assert 0.0 <= respondent <= 100.0


def test_normalize_fault_split_falls_back_to_even_split_when_both_zero():
    claimant, respondent = _normalize_fault_split(0.0, 0.0)
    assert (claimant, respondent) == (50.0, 50.0)


async def test_claimant_agent_builds_case(fake_llm_router):
    router = fake_llm_router(
        {
            "case_summary": "Wrong file format delivered",
            "claims": [{"statement": "PNG instead of SVG", "evidence_indices": [0]}],
            "requested_remedy": "Full refund",
        }
    )
    agent = ClaimantAgent(router)

    result = await agent.run(
        task_description="Design a logo",
        agreed_deliverable="SVG",
        actual_deliverable="PNG",
        claimant_evidence="[0] screenshot",
    )

    assert result.status == AgentStatus.OK
    assert result.output["requested_remedy"] == "Full refund"


async def test_evidence_verifier_degraded_without_match_score(fake_llm_router):
    router = fake_llm_router({"discrepancies": [], "evidence_timeline": []})
    agent = EvidenceVerifierAgent(router)

    result = await agent.run(
        agreed_deliverable="SVG", actual_deliverable="PNG", all_evidence="(none)"
    )

    assert result.status == AgentStatus.DEGRADED


async def test_arbitrator_uses_judge_model(fake_llm_router):
    router = fake_llm_router(
        {
            "verdict": "Respondent at fault",
            "claimant_fault_percentage": 10.0,
            "respondent_fault_percentage": 90.0,
            "refund_recommendation_percentage": 85.0,
            "executive_summary": "summary",
            "reasoning": "reasoning",
            "counter_arguments": [],
            "verdict_confidence": 0.8,
        }
    )
    agent = ArbitratorAgent(router)

    result = await agent.run(
        claimant_case={},
        respondent_defense={},
        evidence_assessment={},
        claimant_reputation={},
        respondent_reputation={},
    )

    assert result.status == AgentStatus.OK
    assert result.confidence == 0.8


def test_arbitration_confidence_zero_with_no_evidence():
    confidence = compute_arbitration_confidence(evidence_count=0, match_score=0.0, discrepancies=[])
    assert confidence["overall"] == 0.0


def test_arbitration_confidence_high_when_decisive_and_low_severity():
    confidence = compute_arbitration_confidence(
        evidence_count=4,
        match_score=0.95,
        discrepancies=[{"description": "minor", "severity": 0.1}],
    )
    assert confidence["overall"] > 0.7


def test_reputation_drops_when_at_fault():
    reputation = AgentReputation(
        wallet_id="0xtest", trust_score=75.0, disputes_total=0, disputes_at_fault=0,
        avg_fault_percentage=0.0, completed_tasks=0,
    )
    apply_dispute_outcome(reputation, fault_percentage=90.0)

    assert reputation.disputes_total == 1
    assert reputation.disputes_at_fault == 1
    assert reputation.trust_score < 75.0
    assert standing_label(reputation.trust_score) in {"Neutral", "Flagged"}


def test_format_dispute_evidence_includes_verification_only_when_requested():
    evidence = [
        {
            "submitted_by": "respondent",
            "evidence_type": "tx_reference",
            "content": "0xabc paid on base",
            "verification_status": "not_found",
        }
    ]
    without_verification = format_dispute_evidence(evidence)
    with_verification = format_dispute_evidence(evidence, include_verification=True)

    assert "ON-CHAIN CHECK" not in without_verification
    assert "ON-CHAIN CHECK" in with_verification
    assert "CONTRADICTED" in with_verification


def test_evidence_needing_forced_discrepancy_flags_only_contradicted_statuses():
    evidence = [
        {"submitted_by": "claimant", "verification_status": "confirmed_match"},
        {"submitted_by": "respondent", "verification_status": "not_found"},
        {"submitted_by": "respondent", "verification_status": "pending"},
    ]
    flagged = evidence_needing_forced_discrepancy(evidence)
    assert len(flagged) == 1
    assert flagged[0]["index"] == 1
    assert flagged[0]["status"] == "not_found"


def test_chain_verification_safety_net_appends_discrepancy_llm_missed():
    evidence = [{"submitted_by": "respondent", "verification_status": "not_found"}]
    llm_output = {"match_score": 0.9, "discrepancies": []}  # LLM missed the fabricated tx

    result = _apply_chain_verification_safety_net(llm_output, evidence)

    assert len(result["discrepancies"]) == 1
    assert result["discrepancies"][0]["severity"] >= 0.8
    assert result["match_score"] == 0.9  # untouched - safety net only adds signal


def test_chain_verification_safety_net_is_noop_with_no_flagged_evidence():
    evidence = [{"submitted_by": "claimant", "verification_status": "confirmed_match"}]
    llm_output = {"match_score": 0.9, "discrepancies": [{"description": "minor", "severity": 0.2}]}

    result = _apply_chain_verification_safety_net(llm_output, evidence)

    assert result == llm_output


def test_arbitration_confidence_high_when_chain_evidence_confirmed():
    confidence = compute_arbitration_confidence(
        evidence_count=2, match_score=0.9, discrepancies=[],
        chain_verification_statuses=["confirmed_match"],
    )
    assert confidence["chain_evidence_integrity"] == 1.0


def test_arbitration_confidence_low_when_chain_evidence_contradicted():
    confidence = compute_arbitration_confidence(
        evidence_count=2, match_score=0.9, discrepancies=[],
        chain_verification_statuses=["not_found"],
    )
    assert confidence["chain_evidence_integrity"] == 0.0
    assert confidence["overall"] < 0.7  # a fabricated tx should visibly drag overall confidence down


def test_arbitration_confidence_neutral_when_no_chain_evidence_submitted():
    confidence = compute_arbitration_confidence(evidence_count=2, match_score=0.9, discrepancies=[])
    assert confidence["chain_evidence_integrity"] == 0.5


def test_reputation_rises_when_not_at_fault():
    reputation = AgentReputation(
        wallet_id="0xtest", trust_score=75.0, disputes_total=0, disputes_at_fault=0,
        avg_fault_percentage=0.0, completed_tasks=0,
    )
    apply_dispute_outcome(reputation, fault_percentage=5.0)

    assert reputation.disputes_at_fault == 0
    assert reputation.trust_score > 75.0


def _fresh_reputation(trust_score: float = 75.0) -> AgentReputation:
    return AgentReputation(
        wallet_id="0xtest", trust_score=trust_score, disputes_total=0, disputes_at_fault=0,
        avg_fault_percentage=0.0, completed_tasks=0,
    )


def test_low_confidence_verdict_moves_trust_score_less_than_high_confidence():
    low_conf = _fresh_reputation()
    high_conf = _fresh_reputation()

    apply_dispute_outcome(low_conf, fault_percentage=90.0, confidence_score=0.2, escrow_amount=1000)
    apply_dispute_outcome(high_conf, fault_percentage=90.0, confidence_score=0.95, escrow_amount=1000)

    assert (75.0 - low_conf.trust_score) < (75.0 - high_conf.trust_score)


def test_small_escrow_moves_trust_score_less_than_large_escrow():
    small_escrow = _fresh_reputation()
    large_escrow = _fresh_reputation()

    apply_dispute_outcome(small_escrow, fault_percentage=90.0, confidence_score=0.9, escrow_amount=1)
    apply_dispute_outcome(large_escrow, fault_percentage=90.0, confidence_score=0.9, escrow_amount=50_000)

    assert (75.0 - small_escrow.trust_score) < (75.0 - large_escrow.trust_score)


def test_reputation_swing_stays_bounded_at_extremes():
    # Even a maximally-confident, maximally-large-escrow dispute must not be
    # able to swing trust score outside a sane single-dispute bound.
    reputation = _fresh_reputation(trust_score=95.0)
    apply_dispute_outcome(reputation, fault_percentage=100.0, confidence_score=1.0, escrow_amount=10_000_000)
    assert reputation.trust_score >= 95.0 * (1 - 0.35) - 1  # never more than the max learning rate implies


def test_reputation_update_with_no_escrow_still_moves_score():
    # Missing escrow_amount (None) must not zero out the update entirely -
    # it should still count, just as a low-stakes case.
    reputation = _fresh_reputation()
    apply_dispute_outcome(reputation, fault_percentage=90.0, confidence_score=0.9, escrow_amount=None)
    assert reputation.trust_score < 75.0
