from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime


class PostDetail(PostRead):
    comment_count: int = 0
    like_count: int = 0


class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_id: int
    text: str
    created_at: datetime


class LikeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_id: int


class LikesSummary(BaseModel):
    count: int
    likes: list[LikeRead]


class LikeToggleResponse(BaseModel):
    liked: bool
    like_count: int
    message: str


class EmailNotificationRequest(BaseModel):
    to_email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)


# --- Subscription & billing (Task 7) ---


class SubscribeRequest(BaseModel):
    plan_id: int = Field(..., ge=1)


class SubscriptionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    duration: int


class BillingHistoryRead(BaseModel):
    id: int
    plan: SubscriptionPlanRead
    start_date: datetime
    end_date: datetime
    invoice: str
    transaction_id: str


class SubscribeResponse(BaseModel):
    message: str
    billing: BillingHistoryRead


class ActiveSubscriptionResponse(BaseModel):
    billing: BillingHistoryRead
