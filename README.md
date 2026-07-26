# TruthOS

> Evidence-Driven Multi-Agent Intelligence Platform

TruthOS plans, researches, verifies, debates and explains every important
answer instead of just generating one. A Planner Agent decomposes a query,
specialist agents gather evidence through a hybrid RAG + knowledge-graph
pipeline, an AI Courtroom (Research, Fact Checker, Critic) debates the
findings, a Judge issues a verdict, and a Writer produces a layered report
with a transparent Confidence DNA score.

```
User -> Planner -> Task Decomposition -> Specialist Agents -> Retrieval
      -> Truth Engine -> Debate Engine (Fact Checker + Critic) -> Judge
      -> Writer -> Layered Report
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the pieces fit
together and [docs/SETUP.md](docs/SETUP.md) to run it locally.

## Stack

| Layer          | Tech                                                             |
| -------------- | ----------------------------------------------------------------- |
| Frontend       | Next.js 15, TypeScript, TailwindCSS, shadcn/ui-style components, Framer Motion, Zustand |
| Backend        | FastAPI, Python 3.12, LangGraph, Pydantic, SQLAlchemy (async)     |
| Databases      | PostgreSQL, Redis, Neo4j                                          |
| LLM routing    | OpenRouter (retry + fallback model)                               |
| Observability  | structlog, Langfuse, PostHog hooks                                |
| Deployment     | Docker / docker-compose, Railway, Vercel                          |

## Repository layout

```
truthos/
  backend/    FastAPI app: agents, prompts, RAG, graph, memory, API, tests
  frontend/   Next.js app: chat UI, layered report, evidence dashboard
  docs/       Architecture and setup docs
docker-compose.yml   Postgres + Redis + Neo4j + backend + frontend
```

## Quick start

```bash
cp .env.example .env            # fill in OPENROUTER_API_KEY, TAVILY_API_KEY, etc.
docker compose up --build       # starts every service
```

Backend: http://localhost:8000/docs · Frontend: http://localhost:3000

For running the backend/frontend outside Docker (faster iteration), see
[docs/SETUP.md](docs/SETUP.md).

## Status

This is the MVP slice from the product spec: authentication, chat, planner,
truth engine, hybrid RAG, knowledge graph, memory, evidence dashboard and
layered reports are implemented end-to-end and covered by tests. Voice, MCP,
A2A, a workflow builder, enterprise workspaces and a plugin marketplace are
future work (see the master spec).

**Before production use**: rotate `APP_SECRET_KEY`/`JWT_SECRET_KEY`, supply
real API keys in `.env`, and review `docs/SETUP.md`'s security notes.
