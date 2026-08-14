"""
FastAPI Router for Authentication Endpoints
-------------------------------------------
Provides REST API endpoints for user registration, authentication, and profile checks.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr
import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    confirm_password: str = ""
    role: str = "candidate"


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    user_id: str | None = None
    full_name: str | None = None
    email: str | None = None
    role: str | None = None
    token: str | None = None


def get_current_user(authorization: str | None = Header(None)) -> dict:
    """FastAPI Dependency for protected routes."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing."
        )
    
    token = authorization.replace("Bearer ", "").strip()
    payload = auth_service.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )
    return payload


@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    """Endpoint for user registration."""
    ok, msg, data = auth_service.register_user(
        full_name=req.full_name,
        email=req.email,
        password=req.password,
        confirm_password=req.confirm_password,
        role=req.role
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    
    return AuthResponse(
        success=True,
        message=msg,
        user_id=data.get("user_id"),
        full_name=data.get("full_name"),
        email=data.get("email"),
        role=data.get("role"),
        token=data.get("token")
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    """Endpoint for user login."""
    ok, msg, data = auth_service.authenticate_user(email=req.email, password=req.password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)
    
    return AuthResponse(
        success=True,
        message=msg,
        user_id=data.get("user_id"),
        full_name=data.get("full_name"),
        email=data.get("email"),
        role=data.get("role"),
        token=data.get("token")
    )


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Return currently authenticated user information."""
    return {
        "user_id": current_user.get("sub"),
        "full_name": current_user.get("full_name"),
        "email": current_user.get("email"),
        "role": current_user.get("role")
    }
