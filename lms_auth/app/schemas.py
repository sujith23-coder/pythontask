from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    email: str | None = None
    is_new_user: bool = False


class OAuthLoginResponse(BaseModel):
    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str | None = None


class OTPRequestBody(BaseModel):
    identifier: str = Field(..., description="Email or phone number")
    purpose: str = Field(default="login", pattern="^(login|signup)$")


class OTPVerifyBody(BaseModel):
    identifier: str
    otp: str = Field(..., min_length=4, max_length=8)
    purpose: str = Field(default="login", pattern="^(login|signup)$")
    username: str | None = Field(default=None, description="Required for signup when user does not exist")


class OTPRequestResponse(BaseModel):
    message: str
    expires_in_minutes: int
    purpose: str


class UserMeResponse(BaseModel):
    id: int
    username: str
    email: str | None
    first_name: str
    last_name: str
    social_providers: list[str]
