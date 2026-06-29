from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime

class SeverityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class AlertStatusEnum(str, Enum):
    active = "active"
    resolved = "resolved"
    cancelled = "cancelled"

class AlertResponse(BaseModel):
    alert_id: int
    report_id: int
    severity: SeverityEnum
    status: AlertStatusEnum
    radius_km: float
    message: Optional[str]
    created_at: datetime
    approved_by: Optional[int]

    class Config:
        from_attributes = True

class RiskAssessment(BaseModel):
    severity: str
    score: int
    message: str
    nearest_settlement: str
    distance_km: float
    species_risk: str
    proximity_risk: str