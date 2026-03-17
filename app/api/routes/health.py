from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse, summary="Health check")
def health_check() -> HealthResponse:
    return HealthResponse(message="service is running")
