from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db
from ..limits import limiter
from ..models import UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.ProfileRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, data: schemas.ProfileCreate, db: Session = Depends(get_db)):
    """Public: create an account (password stored hashed). Then obtain JWT via POST /auth/token."""
    if db.query(UserProfile).filter(UserProfile.username == data.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    if db.query(UserProfile).filter(UserProfile.email == data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    profile = UserProfile(
        username=data.username,
        email=data.email,
        bio=data.bio,
        hashed_password=hash_password(data.password),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/token", response_model=schemas.Token)
@limiter.limit("30/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.username == form_data.username).first()
    if not profile or not verify_password(form_data.password, profile.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(str(profile.id))
    return schemas.Token(access_token=token)
