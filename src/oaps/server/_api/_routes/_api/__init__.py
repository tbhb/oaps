from fastapi import APIRouter

from ._health import router as health_router
from ._root import router as root_router

router = APIRouter(prefix="/api")

router.include_router(health_router)
router.include_router(root_router)
