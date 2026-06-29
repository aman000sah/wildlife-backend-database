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
    is_visible: bool = False    # ← NEW
    timestamp: datetime
    # ── ML detection fields (NEW) ──────────────────────────────────────────────
    # Populated directly from the related MLDetection row so the frontend
    # never has to make a second /detection request per report, and never
    # falls back to "unknown" just because a request raced or failed.
    ml_species_detected: Optional[str] = None
    ml_confidence: Optional[float] = None
    ml_is_verified: Optional[bool] = None

    class Config:
        from_attributes = True


# ── Recent Sightings (NEW) ───────────────────────────────────────────────────
# Used by GET /api/alerts/recent. Deliberately leaves out latitude/longitude
# and user_id — per that endpoint's docstring, Recent Sightings is a public-
# facing feed and shouldn't expose exact coordinates or who reported it.
# Still carries the ML fields so the admin/recent-activity UI can show
# confidence without a second /detection round trip.
class RecentSightingResponse(BaseModel):
    report_id: int
    species_reported: str
    image_url: Optional[str]
    condition: ConditionEnum
    status: StatusEnum
    is_visible: bool = False
    timestamp: datetime
    ml_species_detected: Optional[str] = None
    ml_confidence: Optional[float] = None
    ml_is_verified: Optional[bool] = None

    class Config:
        from_attributes = True
