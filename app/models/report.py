from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ConditionEnum(str, enum.Enum):
    normal = "normal"
    injured = "injured"
    rage = "rage"
    poached = "poached"


class StatusEnum(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    suspicious = "suspicious"


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    species_reported = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    image_hash = Column(String, nullable=True, unique=True)
    condition = Column(Enum(ConditionEnum), default=ConditionEnum.normal)
    status = Column(Enum(StatusEnum), default=StatusEnum.pending)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_duplicate = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=False)   # ← NEW: set True when alert approved + broadcast on
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="reports")
    ml_detection = relationship("MLDetection", backref="report", uselist=False)

    # ── Convenience proxies (NEW) ───────────────────────────────────────────
    # Let ReportResponse read ML fields straight off the Report object
    # (via from_attributes) instead of requiring a second query per report.
    @property
    def ml_species_detected(self):
        return self.ml_detection.species_detected if self.ml_detection else None

    @property
    def ml_confidence(self):
        return self.ml_detection.confidence if self.ml_detection else None

    @property
    def ml_is_verified(self):
        return self.ml_detection.is_verified if self.ml_detection else None
