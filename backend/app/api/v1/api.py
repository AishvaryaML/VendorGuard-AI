from fastapi import APIRouter
from app.api.v1.endpoints import health, vendors, monitoring, alerts, rag, assistant, agentic

api_router = APIRouter()

# Include feature sub-routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG Foundation"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["Assistant API"])
api_router.include_router(agentic.router, prefix="/agentic", tags=["Agentic Workflow"])
