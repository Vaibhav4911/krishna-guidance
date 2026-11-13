from fastapi import APIRouter

router = APIRouter()


@router.get("/health/live")
def live():
    return {"status": "ok"}


@router.get("/health/ready")
def ready():
    return {
        "status": "ready",
        "services": {
            "database": "pending",
            "vector_store": "pending",
            "ai_provider": "configured",
        },
    }
