from app.agents.fact_checker import FactCheckerAgent
from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.schemas.agent import AgentStatus


async def test_planner_agent_returns_ok_when_subtasks_present(fake_llm_router):
    router = fake_llm_router(
        {
            "sub_tasks": [
                {
                    "objective": "check X",
                    "assigned_agent": "research",
                    "requires_web": True,
                    "requires_kg": False,
                }
            ],
            "plan_rationale": "single-step lookup",
        }
    )
    agent = PlannerAgent(router)

    result = await agent.run(query="Is X true?")

    assert result.status == AgentStatus.OK
    assert result.confidence > 0.5
    assert len(result.output["sub_tasks"]) == 1
    assert router.calls[0]["agent_name"] == "planner"


async def test_planner_agent_degraded_when_no_subtasks(fake_llm_router):
    router = fake_llm_router({"sub_tasks": [], "plan_rationale": "nothing to decompose"})
    agent = PlannerAgent(router)

    result = await agent.run(query="")

    assert result.status == AgentStatus.DEGRADED
    assert result.confidence < 0.5


async def test_research_agent_computes_mean_claim_confidence(fake_llm_router):
    router = fake_llm_router(
        {
            "claims": [
                {"statement": "A is true", "evidence_indices": [0], "confidence": 0.9},
                {"statement": "B is true", "evidence_indices": [1], "confidence": 0.7},
            ],
            "summary": "case built",
        }
    )
    agent = ResearchAgent(router)

    result = await agent.run(objective="investigate A and B", evidence_chunks=[])

    assert result.status == AgentStatus.OK
    assert abs(result.confidence - 0.8) < 1e-6


async def test_fact_checker_confidence_reflects_verified_ratio(fake_llm_router):
    router = fake_llm_router(
        {
            "verifications": [
                {"claim": "A", "verdict": "VERIFIED", "reason": "matches evidence 0", "evidence_indices": [0]},
                {"claim": "B", "verdict": "CONTRADICTED", "reason": "conflicts with evidence 1", "evidence_indices": [1]},
            ]
        }
    )
    agent = FactCheckerAgent(router)

    result = await agent.run(claims=[{"statement": "A"}, {"statement": "B"}], evidence_chunks=[])

    assert result.confidence == 0.5
