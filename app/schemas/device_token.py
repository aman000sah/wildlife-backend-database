from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DeviceTokenCreate(BaseModel):
    token: str
    device_name: Optional[str] = None

class DeviceTokenResponse(BaseModel):
    token_id: int
    token: str
    device_name: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True