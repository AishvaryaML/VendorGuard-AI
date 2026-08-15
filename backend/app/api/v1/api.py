from fastapi import APIRouter
from app.api.v1.endpoints import health, vendors

api_router = APIRouter()

# Include feature sub-routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
