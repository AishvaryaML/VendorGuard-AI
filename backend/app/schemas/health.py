from datetime import datetime
from pydantic import BaseModel, Field


class SystemHealthResponse(BaseModel):
    status: str = Field(default="healthy", example="healthy")
    app_name: str
    environment: str
    version: str = "1.0.0"
    database: str = Field(default="connected", example="connected")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
