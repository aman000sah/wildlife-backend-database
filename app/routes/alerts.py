from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.alert import Alert, SeverityEnum, AlertStatusEnum
from app.models.report import Report, StatusEnum
from app.models.user import User, UserRole
from app.schemas.alert import AlertResponse, RiskAssessment
from app.core.security import get_current_user
from app.services.risk_service import calculate_risk_score
from app.services.fcm_service import (
    send_alert_to_topic,
    send_bulk_notifications,
    send_alert_notification
)

router = APIRouter()

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.put("/update-token")
def update_fcm_token(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update FCM device token for current user."""
    current_user.fcm_token = token
    db.commit()
    return {"message": "FCM token updated successfully"}

@router.get("/all", response_model=List[AlertResponse])
def get_all_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Alert).filter(
        Alert.status == AlertStatusEnum.active
    ).all()

@router.get("/risk/{report_id}", response_model=RiskAssessment)
def assess_risk(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    risk = calculate_risk_score(
        species=report.species_reported,
        condition=report.condition,
        latitude=report.latitude,
        longitude=report.longitude
    )
    return risk

@router.post("/approve/{report_id}", response_model=AlertResponse)
def approve_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status == StatusEnum.verified:
        raise HTTPException(status_code=400, detail="Report already approved")

    # Calculate risk
    risk = calculate_risk_score(
        species=report.species_reported,
        condition=report.condition,
        latitude=report.latitude,
        longitude=report.longitude
    )

    # Update report status
    report.status = StatusEnum.verified
    db.commit()

    # Create alert
    alert = Alert(
        report_id=report_id,
        severity=risk["severity"],
        status=AlertStatusEnum.active,
        radius_km=10.0 if risk["severity"] in ["high", "critical"] else 5.0,
        message=risk["message"],
        approved_by=admin.user_id
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Send FCM notification to topic based on nearest settlement
    settlement = risk.get("nearest_settlement", "general")
    topic = f"{settlement.lower()}_alerts"

    notification_title = f"🚨 Wildlife Alert - {risk['severity'].upper()}"
    notification_body = risk["message"]
    notification_data = {
        "alert_id": str(alert.alert_id),
        "report_id": str(report_id),
        "severity": risk["severity"],
        "species": report.species_reported,
        "latitude": str(report.latitude),
        "longitude": str(report.longitude)
    }

    # Send to topic (all subscribed users)
    fcm_result = send_alert_to_topic(
        topic=topic,
        title=notification_title,
        body=notification_body,
        data=notification_data
    )

    # Also notify all users with FCM tokens in DB
    users_with_tokens = db.query(User).filter(
        User.fcm_token.isnot(None)
    ).all()

    if users_with_tokens:
        tokens = [u.fcm_token for u in users_with_tokens]
        send_bulk_notifications(
            tokens=tokens,
            title=notification_title,
            body=notification_body,
            data=notification_data
        )

    return alert

@router.post("/reject/{report_id}")
def reject_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = StatusEnum.rejected
    db.commit()

    return {"message": f"Report {report_id} rejected successfully"}

@router.post("/resolve/{alert_id}")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatusEnum.resolved
    db.commit()
    return {"message": f"Alert {alert_id} resolved successfully"}

@router.post("/test-notification")
def test_notification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test FCM notification for current user."""
    if not current_user.fcm_token:
        raise HTTPException(
            status_code=400,
            detail="No FCM token registered. Update your token first."
        )

    result = send_alert_notification(
        token=current_user.fcm_token,
        title="🐾 Test Alert",
        body="Wildlife alert system is working!",
        data={"type": "test"}
    )
    return result