# Setup

## Option A: Docker Compose (everything)

```bash
cp .env.example .env
# fill in at least OPENROUTER_API_KEY, TAVILY_API_KEY, APP_SECRET_KEY, JWT_SECRET_KEY
docker compose up --build
```

This starts Postgres, Redis, Neo4j, the FastAPI backend
(`localhost:8000`) and the Next.js frontend (`localhost:3000`). Run
migrations once the Postgres container is healthy:

```bash
docker compose exec backend alembic upgrade head
```

## Option B: run backend/frontend locally, infra in Docker

Faster edit-reload loop during development.

```bash
docker compose up postgres redis neo4j
```

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # or export the vars another way
alembic upgrade head
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest app/tests -q
```

The test suite doesn't need Postgres/Redis/Neo4j running - agent and
retrieval tests use fakes/mocks for the LLM router and search tools; only
`test_auth.py`'s JWT/password tests hit real crypto libraries.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

## Required API keys

| Key | Used for | Behavior if missing |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | All agent LLM calls | Agents return `FAILED`/`DEGRADED` results; pipeline still runs but with empty verdicts |
| `TAVILY_API_KEY` | Web search in retrieval | Web search returns no results, so there's nothing for BM25 to rank |
| `SEMANTIC_SCHOLAR_API_KEY` | Academic search | Optional - unauthenticated requests are rate-limited but still work |
| `COINGECKO_API_KEY` / `ALPHAVANTAGE_API_KEY` | Finance specialist agent | Finance agent runs with no market data (low confidence, not silence) |

Generate strong secrets for `APP_SECRET_KEY` and `JWT_SECRET_KEY`, e.g.:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Database migrations

Migrations live in `backend/alembic/versions/`. After changing a model in
`backend/app/db/models/`, generate a new revision:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Security notes before deploying

- Rotate every secret in `.env` - the checked-in `.env.example` values are
  placeholders only.
- `APP_ALLOWED_ORIGINS` in production should list your real frontend origin(s),
  not `*`.
- The JWT access token is short-lived (60 min default); the refresh token
  (7 days default) is what the frontend should silently exchange on 401s -
  wire that up in `frontend/src/lib/api.ts` before shipping (the endpoint
  `POST /api/v1/auth/refresh` already exists).
- Put the backend behind HTTPS and set secure cookie/storage practices if you
  move tokens out of `localStorage`.
