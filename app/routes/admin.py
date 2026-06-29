from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.report import Report, StatusEnum
from app.models.user import User
from app.core.security import get_current_user
from datetime import datetime, timezone

router = APIRouter()


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pending_count = db.query(Report).filter(
        Report.status == StatusEnum.pending
    ).count()

    verified_count = db.query(Report).filter(
        Report.status == StatusEnum.verified
    ).count()

    rejected_count = db.query(Report).filter(
        Report.status == StatusEnum.rejected
    ).count()

    today = datetime.now(timezone.utc).date()
    verified_today = sum(
        1 for r in db.query(Report).filter(Report.status == StatusEnum.verified).all()
        if r.timestamp and r.timestamp.date() == today
    )

    return {
        "pending_reviews": pending_count,
        "verified_total": verified_count,     # all-time verified count (for the "Verified" card)
        "rejected_total": rejected_count,      # all-time rejected count (for the "Rejected" card)
        "verified_today": verified_today,      # kept for backward compatibility
    }


@router.put("/reports/{report_id}/status")
def update_report_status(
    report_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        return {"detail": "Report not found"}

    new_status = payload.get("status")
    if new_status == "verified":
        report.status = StatusEnum.verified
        # ✅ No more broadcast gate — verified reports are visible right away.
        report.is_visible = True
    elif new_status == "rejected":
        report.status = StatusEnum.rejected
        report.is_visible = False

    db.commit()
    db.refresh(report)
    return {"report_id": report.report_id, "status": report.status, "is_visible": report.is_visible}
