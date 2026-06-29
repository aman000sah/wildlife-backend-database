from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.alert import Alert, SeverityEnum, AlertStatusEnum
from app.models.report import Report, StatusEnum
from app.models.user import User, UserRole
from app.schemas.alert import AlertResponse, RiskAssessment
from app.core.security import get_current_user
from app.schemas.report import ReportResponse, RecentSightingResponse
from app.services.risk_service import calculate_risk_score

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("", response_model=List[AlertResponse])
def get_all_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Alert).filter(
        Alert.status == AlertStatusEnum.active
    ).order_by(Alert.alert_id.desc()).all()


@router.get("/all", response_model=List[AlertResponse])
def get_all_alerts_alias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_all_alerts(db=db, current_user=current_user)


@router.get("/risk/{report_id}", response_model=RiskAssessment)
def assess_risk(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    risk = calculate_risk_score(
        species=report.species_reported,
        condition=report.condition,
        latitude=report.latitude,
        longitude=report.longitude,
    )
    return risk


# ✅ Admin approval now creates an active alert and makes the report visible.
# This means approved reports appear in alerts and heatmap, while rejected
# reports remain only in recent sightings.
@router.post("/approve/{report_id}", response_model=Optional[AlertResponse])
def approve_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status == StatusEnum.verified:
        raise HTTPException(status_code=400, detail="Report already approved")

    risk = calculate_risk_score(
        species=report.species_reported,
        condition=report.condition,
        latitude=report.latitude,
        longitude=report.longitude,
    )

    report.status = StatusEnum.verified
    report.is_visible = True
    db.commit()

    alert = Alert(
        report_id=report_id,
        severity=risk["severity"],
        status=AlertStatusEnum.active,
        radius_km=10.0 if risk["severity"] in ["high", "critical"] else 5.0,
        message=risk["message"],
        approved_by=admin.user_id,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/reject/{report_id}")
def reject_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = StatusEnum.rejected
    report.is_visible = False
    db.commit()
    return {"message": f"Report {report_id} rejected successfully"}


@router.post("/resolve/{alert_id}")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatusEnum.resolved
    db.commit()
    return {"message": f"Alert {alert_id} resolved successfully"}


@router.get("/recent", response_model=List[RecentSightingResponse])
def get_recent_sightings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """All verified reports — Recent Sightings only. Location fields are omitted."""
    return db.query(Report).filter(
        Report.status == StatusEnum.verified
    ).order_by(Report.timestamp.desc()).all()


