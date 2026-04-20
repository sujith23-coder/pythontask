from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_profile, get_current_profile_id, hash_password
from ..database import get_db
from ..limits import limiter
from ..models import UserProfile

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post(
    "/",
    response_model=schemas.ProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create profile (authenticated)",
)
@limiter.limit("20/minute")
def create_profile(
    request: Request,
    data: schemas.ProfileCreate,
    _token_profile_id: int = Depends(get_current_profile_id),
    db: Session = Depends(get_db),
):
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


@router.get("/me", response_model=schemas.ProfileRead)
@limiter.limit("60/minute")
def read_me(request: Request, current: UserProfile = Depends(get_current_profile)):
    return current


@router.get("/{profile_id}", response_model=schemas.ProfileRead)
@limiter.limit("120/minute")
def read_profile(
    request: Request,
    profile_id: int,
    _token_profile_id: int = Depends(get_current_profile_id),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=schemas.ProfileRead)
@limiter.limit("30/minute")
def update_profile(
    request: Request,
    profile_id: int,
    data: schemas.ProfileUpdate,
    current: UserProfile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    if current.id != profile_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this profile")
    if data.username is None and data.email is None and data.bio is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if data.username is not None:
        taken = (
            db.query(UserProfile)
            .filter(UserProfile.username == data.username, UserProfile.id != profile_id)
            .first()
        )
        if taken:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
        profile.username = data.username
    if data.email is not None:
        taken = (
            db.query(UserProfile).filter(UserProfile.email == data.email, UserProfile.id != profile_id).first()
        )
        if taken:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        profile.email = data.email
    if data.bio is not None:
        profile.bio = data.bio
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
def delete_profile(
    request: Request,
    profile_id: int,
    current: UserProfile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    if current.id != profile_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete this profile")
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    db.delete(profile)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
