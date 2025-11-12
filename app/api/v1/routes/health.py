from fastapi import APIRouter
from typing import Dict

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=Dict[str, str])
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Dict with status indicating the service is healthy
    """
    return {"status": "healthy"}
