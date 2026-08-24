from fastapi import APIRouter
from app.api.v1.endpoints import health, vendors, monitoring, alerts

api_router = APIRouter()

# Include feature sub-routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
