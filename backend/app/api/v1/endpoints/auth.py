# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ....db.database import get_db
from ....auth.auth import authenticate_user, create_access_token, create_user, get_user_by_email, ACCESS_TOKEN_EXPIRE_MINUTES
from ....auth.dependencies import get_current_active_user
from ....db.models.project import User
from ....services.security_logger import security_logger, log_login_attempt

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None
):
    """Login endpoint to get access token (OAuth2 compatible)"""
    user_ip = request.client.host if request and request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "") if request else ""
    
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Log failed login attempt
        log_login_attempt(
            user_email=form_data.username,
            success=False,
            user_ip=user_ip,
            user_agent=user_agent,
            error_message="Invalid credentials"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log successful login
    log_login_attempt(
        user_email=user.email,
        success=True,
        user_ip=user_ip,
        user_agent=user_agent
    )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login_with_json(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    request: Request = None
):
    """Login endpoint with JSON request body"""
    user_ip = request.client.host if request and request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "") if request else ""
    
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        # Log failed login attempt
        log_login_attempt(
            user_email=login_data.email,
            success=False,
            user_ip=user_ip,
            user_agent=user_agent,
            error_message="Invalid credentials"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log successful login
    log_login_attempt(
        user_email=user.email,
        success=True,
        user_ip=user_ip,
        user_agent=user_agent
    )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = create_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )
    
    return user


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user