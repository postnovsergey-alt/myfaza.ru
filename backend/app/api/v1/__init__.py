from fastapi import APIRouter

from app.api.v1 import auth, cycles, health, logs, me, predictions, push, settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(cycles.router)
api_router.include_router(predictions.router)
api_router.include_router(logs.router)
api_router.include_router(settings.router)
api_router.include_router(push.router)
api_router.include_router(me.router)
