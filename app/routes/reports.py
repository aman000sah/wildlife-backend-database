from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.report import Report, ConditionEnum
from app.models.user import User
from app.schemas.report import ReportResponse
from app.core.security import get_current_user

router = APIRouter()

@router.post("/submit", response_model=ReportResponse, status_code=201)
async def submit_report(
    species_reported: str = Form(...),
    condition: ConditionEnum = Form(ConditionEnum.normal),
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_report = Report(
        user_id=current_user.user_id,
        species_reported=species_reported,
        condition=condition,
        latitude=latitude,
        longitude=longitude,
        image_url=None
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report

@router.get("/all", response_model=List[ReportResponse])
def get_all_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Report).all()

@router.get("/my", response_model=List[ReportResponse])
def get_my_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Report).filter(Report.user_id == current_user.user_id).all()

@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(Report).filter(Report.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report