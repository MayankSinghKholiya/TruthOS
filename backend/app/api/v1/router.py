from fastapi import APIRouter

from app.api.v1 import api_keys, auth, chat, disputes, health, reports, telegram

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(reports.router)
api_router.include_router(disputes.router)
api_router.include_router(api_keys.router)
api_router.include_router(telegram.router)
