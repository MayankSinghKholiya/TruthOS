"""Regression tests for the "LLM returns a number slightly outside [0,1]"
bug class: AgentResult.confidence has a hard Pydantic ge=0/le=1 constraint,
so an unclamped value doesn't just look wrong - it crashes the agent's run()
with a validation error. Each of these agents blends an LLM-supplied number
into its confidence and must clamp before constructing AgentResult."""
from app.agents.arbitrator import ArbitratorAgent
from app.agents.critic import CriticAgent
from app.agents.judge import JudgeAgent
from app.agents.research import ResearchAgent
from app.agents.truth import TruthAgent
from app.services.confidence import compute_arbitration_confidence


async def test_critic_clamps_out_of_range_severity(fake_llm_router):
    router = fake_llm_router(
        {
            "skeptic_objections": [{"objection": "x", "targets_claim": "c", "severity": 5.0}],
            "devils_advocate_case": {"summary": "s", "key_points": []},
        }
    )
    result = await CriticAgent(router).run(facts={}, claims=[])
    assert 0.0 <= result.confidence <= 1.0


async def test_research_clamps_out_of_range_claim_confidence(fake_llm_router):
    router = fake_llm_router(
        {"claims": [{"statement": "x", "evidence_indices": [0], "confidence": 42.0}], "summary": "s"}
    )
    result = await ResearchAgent(router).run(objective="x", evidence_chunks=[])
    assert 0.0 <= result.confidence <= 1.0


async def test_truth_clamps_out_of_range_certainty(fake_llm_router):
    router = fake_llm_router(
        {
            "reconciled_facts": [{"statement": "x", "certainty": -3.0, "supporting_evidence_indices": []}],
            "opinions": [],
            "unresolved_uncertainty": [],
            "entity_ambiguity": {"is_ambiguous": False, "explanation": ""},
        }
    )
    result = await TruthAgent(router).run(
        research_claims=[], fact_check_findings=[], evidence_consistency={}, critic_objections=[]
    )
    assert 0.0 <= result.confidence <= 1.0


async def test_truth_clamps_negative_confidence_from_many_unresolved_items(fake_llm_router):
    router = fake_llm_router(
        {
            "reconciled_facts": [{"statement": "x", "certainty": 0.9, "supporting_evidence_indices": []}],
            "opinions": [],
            # 25 items * 0.05 penalty each would drive the multiplier negative
            "unresolved_uncertainty": [f"item {i}" for i in range(25)],
            "entity_ambiguity": {"is_ambiguous": False, "explanation": ""},
        }
    )
    result = await TruthAgent(router).run(
        research_claims=[], fact_check_findings=[], evidence_consistency={}, critic_objections=[]
    )
    assert 0.0 <= result.confidence <= 1.0


async def test_judge_clamps_out_of_range_verdict_confidence(fake_llm_router):
    router = fake_llm_router(
        {
            "verdict": "x",
            "executive_summary": "s",
            "deep_dive": "d",
            "counter_arguments": [],
            "verdict_confidence": 1.4,
        }
    )
    result = await JudgeAgent(router).run(reconciliation={}, critic_findings={}, fact_check_results={})
    assert 0.0 <= result.confidence <= 1.0


async def test_arbitrator_clamps_out_of_range_verdict_confidence(fake_llm_router):
    router = fake_llm_router(
        {
            "verdict": "x",
            "claimant_fault_percentage": 50.0,
            "respondent_fault_percentage": 50.0,
            "refund_recommendation_percentage": 50.0,
            "executive_summary": "s",
            "reasoning": "r",
            "counter_arguments": [],
            "verdict_confidence": -0.2,
        }
    )
    result = await ArbitratorAgent(router).run(
        claimant_case={}, respondent_defense={}, evidence_assessment={},
        claimant_reputation={}, respondent_reputation={},
    )
    assert 0.0 <= result.confidence <= 1.0


def test_arbitration_confidence_clamps_out_of_range_match_score():
    breakdown = compute_arbitration_confidence(evidence_count=2, match_score=8.0, discrepancies=[])
    assert 0.0 <= breakdown["overall"] <= 1.0
    assert 0.0 <= breakdown["evidence_decisiveness"] <= 1.0


def test_arbitration_confidence_clamps_negative_severity():
    breakdown = compute_arbitration_confidence(
        evidence_count=2, match_score=0.5, discrepancies=[{"severity": -5.0}]
    )
    assert 0.0 <= breakdown["overall"] <= 1.0
    assert 0.0 <= breakdown["narrative_consensus"] <= 1.0
