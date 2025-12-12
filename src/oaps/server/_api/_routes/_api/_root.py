from fastapi import APIRouter

from oaps.server._schemas import RootResponse

router = APIRouter(prefix="", tags=["root"])


@router.get("/")
async def get_root() -> RootResponse:
    return RootResponse(message="Hello, World!")
