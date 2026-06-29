from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class SeverityEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class AlertStatusEnum(str, enum.Enum):
    active = "active"
    resolved = "resolved"
    cancelled = "cancelled"

class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.report_id"), nullable=False)
    location_id = Column(Integer, nullable=True)
    severity = Column(Enum(SeverityEnum), default=SeverityEnum.low)
    status = Column(Enum(AlertStatusEnum), default=AlertStatusEnum.active)
    radius_km = Column(Float, default=5.0)
    message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)

    report = relationship("Report", backref="alert")
    approver = relationship("User", foreign_keys=[approved_by])