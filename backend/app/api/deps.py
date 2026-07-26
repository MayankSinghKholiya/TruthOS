"""FastAPI dependency wiring. This is the composition root: it's the only
place that knows how to assemble services/agents/orchestrator from the
lower-level singletons in app.core.container - routes just Depends() on
these functions and never construct infrastructure themselves."""
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.container import get_http_client, get_neo4j_driver
from app.core.security import decode_token, hash_api_key
from app.db.models.api_key import ApiKey
from app.db.models.telegram import TelegramLink
from app.db.models.user import User
from app.db.session import get_db_session
from app.graph.arbitration_orchestrator import ArbitrationOrchestrator
from app.graph.knowledge_graph import KnowledgeGraph
from app.graph.orchestrator import Orchestrator
from app.memory.episodic import EpisodicMemoryStore
from app.memory.manager import MemoryManager
from app.memory.project import ProjectMemoryStore
from app.rag.hybrid_retriever import HybridRetriever
from app.services.chain_verification import ChainVerificationService, parse_rpc_url_overrides
from app.services.llm_router import LLMRouter
from app.services.market_data import MarketDataService
from app.services.search_tools import SemanticScholarTool, TavilySearchTool
from app.services.telegram_bot import TelegramBotService

_bearer_scheme = HTTPBearer(auto_error=False)
_api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = decode_token(credentials.credentials, expected_type="access")
    user = await db.get(User, UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return user


async def get_agent_api_key(
    api_key: str | None = Depends(_api_key_scheme),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """Resolves an X-API-Key header to the ApiKey record it was issued for.
    This is the agent-callable analog of get_current_user: the caller's
    identity is a wallet (record.wallet_id), not a human account, and it can
    only ever be the wallet its own key was minted for - never a
    caller-supplied wallet_id - so an agent cannot file a dispute claiming to
    be a different agent. record.created_by_user_id is still surfaced so
    agent-filed disputes remain attributable to the human who owns the key,
    the same as anything filed through the human JWT flow."""
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key header")

    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(api_key)))
    record = result.scalar_one_or_none()
    if record is None or record.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key")

    record.last_used_at = datetime.now(timezone.utc)
    return record


def get_telegram_bot_service() -> TelegramBotService:
    return TelegramBotService(get_http_client())


async def get_optional_checker_chat_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    api_key: str | None = Depends(_api_key_scheme),
    db: AsyncSession = Depends(get_db),
) -> str | None:
    """Best-effort, never raises: resolves whichever OPTIONAL caller identity
    is present (human JWT or agent X-API-Key) to their linked Telegram
    chat_id, so a safety check can notify the checker directly when a wallet
    comes back Flagged. Used by GET /reputation/{wallet_id}, which must stay
    fully public - absent, expired, or garbage credentials simply resolve to
    "no one to notify" rather than a 401, so anonymous checking still works
    exactly as before."""
    user_id: UUID | None = None

    if credentials is not None:
        try:
            user_id = UUID(decode_token(credentials.credentials, expected_type="access"))
        except Exception:  # noqa: BLE001 - optional auth: any failure just means "unidentified"
            user_id = None
    elif api_key is not None:
        result = await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(api_key)))
        record = result.scalar_one_or_none()
        if record is not None and record.revoked_at is None:
            user_id = record.created_by_user_id

    if user_id is None:
        return None

    link_result = await db.execute(select(TelegramLink).where(TelegramLink.user_id == user_id))
    link = link_result.scalar_one_or_none()
    return link.telegram_chat_id if link else None


def get_chain_verification_service() -> ChainVerificationService:
    settings = get_settings()
    overrides = parse_rpc_url_overrides(settings.chain_rpc_urls)
    return ChainVerificationService(get_http_client(), overrides)


def get_llm_router() -> LLMRouter:
    return LLMRouter(get_http_client())


def get_hybrid_retriever() -> HybridRetriever:
    web_search = TavilySearchTool(get_http_client())
    academic_search = SemanticScholarTool(get_http_client())
    return HybridRetriever(web_search, academic_search)


def get_knowledge_graph() -> KnowledgeGraph:
    return KnowledgeGraph(get_neo4j_driver())


def get_memory_manager(db: AsyncSession = Depends(get_db)) -> MemoryManager:
    episodic = EpisodicMemoryStore(db)
    project = ProjectMemoryStore(db)
    return MemoryManager(episodic, project)


def get_market_data_service() -> MarketDataService:
    return MarketDataService(get_http_client())


def get_orchestrator(
    llm_router: LLMRouter = Depends(get_llm_router),
    hybrid_retriever: HybridRetriever = Depends(get_hybrid_retriever),
    knowledge_graph: KnowledgeGraph = Depends(get_knowledge_graph),
    memory_manager: MemoryManager = Depends(get_memory_manager),
    market_data: MarketDataService = Depends(get_market_data_service),
) -> Orchestrator:
    return Orchestrator(llm_router, hybrid_retriever, knowledge_graph, memory_manager, market_data)


def get_arbitration_orchestrator(
    llm_router: LLMRouter = Depends(get_llm_router),
    db: AsyncSession = Depends(get_db),
) -> ArbitrationOrchestrator:
    return ArbitrationOrchestrator(llm_router, db)
