import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator
import re
from sqlalchemy.orm import Session

from logger import logger

# Security configurations
SECRET_KEY = os.getenv("SECRET_KEY", "your-very-long-and-random-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3

# Password and validation helpers
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator('username')
    def validate_username(cls, v):
        if not re.match("^[a-zA-Z0-9_]{3,20}$", v):
            raise ValueError("Username must be 3-20 characters, alphanumeric")
        return v

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search("[A-Z]", v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search("[a-z]", v):
            raise ValueError("Password must contain lowercase letter")
        if not re.search("[0-9]", v):
            raise ValueError("Password must contain a number")
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password: str, hashed_password: str):
    """Verify user password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    """Hash user password"""
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user credentials"""
    from models import User
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def get_user(db: Session, username: str):
    """Get user by username"""
    from models import User
    return db.query(User).filter(User.username == username).first()

def get_db():
    """Database session generator"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)  # Use Depends to inject the database session
):
    """Extract current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error":"Could not validate credentials. Please Login again as JWT might have expired."},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    logger.info("[VALID] User check successful!")
    return user

