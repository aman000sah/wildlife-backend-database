from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class MLDetection(Base):
    __tablename__ = "ml_detections"

    detection_id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.report_id"), nullable=False)
    species_detected = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    is_verified = Column(Boolean, default=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())