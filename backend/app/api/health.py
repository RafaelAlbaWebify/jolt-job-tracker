from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "jolt-backend",
        "message": "JOLT backend is running",
    }
