from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter()


# ── POST /api/auth/register ───────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ✅ SECURITY: role is never read from the client payload. Every
    # self-registered account is a plain "user". Admin accounts are only
    # ever created via a direct SQL UPDATE/INSERT in pgAdmin.
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        password=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ── POST /api/auth/login ──────────────────────────────────────────────────────
# Returns: { access_token, token_type, user: { user_id, name, email, role } }
# Flutter caches the 'user' object in SharedPreferences for the username display.
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(
        {"sub": str(user.user_id), "role": user.role}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        # Inline user object — Flutter reads name, email, role from here
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }


# ── GET /api/auth/me ──────────────────────────────────────────────────────────
# Added so Flutter can refresh user info without re-login
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
