from fastapi import APIRouter

from oaps.server._schemas import HealthResponse

router = APIRouter(prefix="", tags=["health"])


@router.get("/health")
async def get_health() -> HealthResponse:
    return HealthResponse(status="healthy")
