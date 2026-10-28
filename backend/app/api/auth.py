"""
Authentication API endpoints.
Implements NFR-01 (authentication, password hashing, secure tokens).
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token
from app.models.user import User, UserRole
from app.schemas.user import UserLogin, UserCreate, UserResponse, Token
from app.services.audit_service import AuditService
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, response: Response, request: Request, db: Session = Depends(get_db)):
    """Authenticate and return JWT token."""
    user = db.query(User).filter(User.email == credentials.email).first()
    audit = AuditService(db)
    ip = request.client.host if request.client else None

    if not user or not verify_password(credentials.password, user.hashed_password):
        audit.log("user.login_failed", detail=f"Failed login for: {credentials.email}", ip_address=ip, status="failure")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is inactive.")

    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # Set session cookie for browser-based sessions
    response.set_cookie(
        key="acs_session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=3600 * 24,
    )

    audit.log("user.login", actor=user, ip_address=ip)
    return Token(access_token=token, user=UserResponse.model_validate(user))


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.delete_cookie("acs_session")
    AuditService(db).log("user.logout", actor=current_user)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new user. Requires admin role."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can register new users.")
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    AuditService(db).log("user.created", actor=current_user, entity_type="User", entity_id=user.id, detail=f"Created user {user.email} with role {user.role.value}")
    return user
