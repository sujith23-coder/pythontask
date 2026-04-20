from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProfileBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    bio: Optional[str] = Field(None, max_length=500)


class ProfileCreate(ProfileBase):
    """Create profile (includes password; not returned in responses)."""

    password: str = Field(..., min_length=8, max_length=128)


class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=64)
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(None, max_length=500)


class ProfileRead(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileCreateResponse(BaseModel):
    profile: ProfileRead
    access_token: str
    token_type: str = "bearer"
