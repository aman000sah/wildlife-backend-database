from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user)
    is_active = Column(Boolean, default=True)
    fcm_token = Column(String, nullable=True)  # ← new field
    created_at = Column(DateTime(timezone=True), server_default=func.now())