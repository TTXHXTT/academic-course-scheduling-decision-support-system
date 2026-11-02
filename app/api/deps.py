"""
FastAPI dependency injection helpers.
Implements NFR-01: server-side authentication and authorization.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(default=None, alias="acs_session"),
) -> User:
    """Get current authenticated user from JWT token (header or cookie)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please sign in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Try Bearer token first, then session cookie
    actual_token = token or session_token
    if not actual_token:
        raise credentials_exception

    payload = decode_token(actual_token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account.")
    return current_user


def require_role(*roles: UserRole):
    """Dependency factory that enforces one of the allowed roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires one of: {[r.value for r in roles]}"
            )
        return current_user
    return role_checker


def can_import_data(current_user: User = Depends(get_current_user)) -> User:
    """Only academic schedulers and admins can import data."""
    if current_user.role not in (
        UserRole.academic_scheduler, UserRole.admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Academic Schedulers and Admins can import data."
        )
    return current_user


def can_view_audit(current_user: User = Depends(get_current_user)) -> User:
    """Only admins and department chairs can view audit logs."""
    if current_user.role not in (
        UserRole.admin, UserRole.department_chair
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and Department Chairs can view audit logs."
        )
    return current_user
