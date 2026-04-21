from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.device_token import DeviceToken
from app.schemas.device_token import DeviceTokenCreate, DeviceTokenResponse
from app.core.security import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
def register_device_token(
    device: DeviceTokenCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Register device token for push notifications"""
    
    # Check if token already exists
    existing = db.query(DeviceToken).filter(DeviceToken.token == device.token).first()
    if existing:
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        logger.info(f"📱 Device token reactivated for user {current_user.user_id}")
        return existing
    
    db_token = DeviceToken(
        user_id=current_user.user_id,
        token=device.token,
        device_name=device.device_name
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    logger.info(f"📱 New device token registered for user {current_user.user_id}")
    return db_token

@router.get("/", response_model=List[DeviceTokenResponse])
def get_device_tokens(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all registered devices for current user"""
    return db.query(DeviceToken).filter(
        DeviceToken.user_id == current_user.user_id,
        DeviceToken.is_active == True
    ).all()

@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def unregister_device(
    token_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Unregister device token"""
    token = db.query(DeviceToken).filter(
        DeviceToken.token_id == token_id,
        DeviceToken.user_id == current_user.user_id
    ).first()
    
    if not token:
        raise HTTPException(status_code=404, detail="Device token not found")
    
    token.is_active = False
    db.commit()
    logger.info(f"📱 Device token deactivated for user {current_user.user_id}")