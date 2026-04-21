from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime

class ConditionEnum(str, Enum):
    normal = "normal"
    injured = "injured"
    rage = "rage"
    poached = "poached"

class StatusEnum(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    suspicious = "suspicious"

class ReportCreate(BaseModel):
    species_reported: str
    condition: ConditionEnum = ConditionEnum.normal
    latitude: float
    longitude: float

class ReportResponse(BaseModel):
    report_id: int
    user_id: int
    species_reported: str
    image_url: Optional[str]
    condition: ConditionEnum
    status: StatusEnum
    latitude: float
    longitude: float
    is_duplicate: bool
    timestamp: datetime

    class Config:
        from_attributes = True