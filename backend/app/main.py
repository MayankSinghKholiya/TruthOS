"""ASGI entrypoint. Wires middleware, exception handling, and the API router."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.container import get_http_client, get_redis, shutdown_container
from app.core.exceptions import TruthOSError
from app.core.logging import configure_logging, get_logger
from app.services.telegram_bot import TelegramBotService
from app.services.telegram_linking import run_linking_poller

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("truthos_starting", env=get_settings().app_env)

    bot = TelegramBotService(get_http_client())
    poller_task = asyncio.create_task(run_linking_poller(bot, get_redis()))

    yield

    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass
    await shutdown_container()
    logger.info("truthos_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TruthOS",
        description="Evidence-Driven Multi-Agent Intelligence Platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(TruthOSError)
    async def truthos_error_handler(request: Request, exc: TruthOSError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(api_router)
    return app


app = create_app()
