from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)

# Спринт 2+: auth, cycles, predictions, logs, settings, stats, push
