"""Health endpoint schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    service: str
    version: str
    environment: str
    timestamp: datetime

