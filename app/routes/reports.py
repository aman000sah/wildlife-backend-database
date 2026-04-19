from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.report import Report, ConditionEnum, StatusEnum
from app.models.ml_detection import MLDetection
from app.models.user import User
from app.schemas.report import ReportResponse
from app.core.security import get_current_user
from app.services.yolo_service import detect_wildlife, generate_image_hash
from app.services.image_service import save_image_locally

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
    image_url = None
    ml_result = None

    # Process image if provided
    if image:
        image_bytes = await image.read()

        # Check for duplicate image
        image_hash = generate_image_hash(image_bytes)
        existing = db.query(Report).filter(Report.image_hash == image_hash).first()
        if existing:
            raise HTTPException(status_code=400, detail="Duplicate image submission detected")

        # Save image locally
        image_url = save_image_locally(image_bytes, image.filename or "upload.jpg")

        # Run YOLOv8 detection
        ml_result = detect_wildlife(image_bytes)

    # Determine report status based on ML result
    if ml_result:
        if ml_result["is_verified"]:
            status = StatusEnum.pending  # verified by ML, waiting admin approval
        else:
            status = StatusEnum.suspicious  # ML couldn't verify
    else:
        status = StatusEnum.pending  # no image submitted

    # Create report
    new_report = Report(
        user_id=current_user.user_id,
        species_reported=species_reported,
        condition=condition,
        latitude=latitude,
        longitude=longitude,
        image_url=image_url,
        image_hash=image_hash if image else None,
        status=status
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    # Save ML detection result
    if ml_result:
        detection = MLDetection(
            report_id=new_report.report_id,
            species_detected=ml_result["species_detected"],
            confidence=ml_result["confidence"],
            is_verified=ml_result["is_verified"]
        )
        db.add(detection)
        db.commit()

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


@router.get("/{report_id}/detection")
def get_report_detection(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    detection = db.query(MLDetection).filter(
        MLDetection.report_id == report_id
    ).first()
    if not detection:
        raise HTTPException(status_code=404, detail="No ML detection found for this report")
    return {
        "report_id": report_id,
        "species_detected": detection.species_detected,
        "confidence": detection.confidence,
        "is_verified": detection.is_verified,
        "detected_at": detection.detected_at
    }