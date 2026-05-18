from fastapi import APIRouter, Depends, HTTPException, status

from accounts.models import SocialAccount
from django.contrib.auth.models import User

from ..auth_utils import create_access_token, get_current_user_id
from ..config import get_settings
from ..schemas import OTPRequestBody, OTPRequestResponse, OTPVerifyBody, TokenResponse, UserMeResponse
from ..services.otp import create_otp_log, send_otp, verify_otp
from ..services.users import get_or_create_user_from_otp

router = APIRouter(prefix="/auth/otp", tags=["OTP Authentication"])


@router.post("/request", response_model=OTPRequestResponse)
def request_otp(body: OTPRequestBody):
    settings = get_settings()
    identifier = body.identifier.strip().lower()

    if body.purpose == "login":
        is_email = "@" in identifier
        exists = (
            User.objects.filter(email__iexact=identifier).exists()
            if is_email
            else User.objects.filter(username=identifier).exists()
        )
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found. Use purpose=signup to register.",
            )

    _, otp = create_otp_log(identifier, body.purpose)
    send_otp(identifier, otp)

    return OTPRequestResponse(
        message="OTP sent successfully",
        expires_in_minutes=settings.otp_expire_minutes,
        purpose=body.purpose,
    )


@router.post("/verify", response_model=TokenResponse)
def verify_otp_login(body: OTPVerifyBody):
    try:
        log = verify_otp(body.identifier, body.otp, body.purpose)
        user, is_new = get_or_create_user_from_otp(
            body.identifier,
            username=body.username,
            purpose=body.purpose,
        )
        log.user = user
        log.save(update_fields=["user"])
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TokenResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        username=user.username,
        email=user.email or None,
        is_new_user=is_new,
    )


@router.get("/me", response_model=UserMeResponse)
def me(user_id: int = Depends(get_current_user_id)):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    providers = list(
        SocialAccount.objects.filter(user=user).values_list("provider", flat=True).distinct()
    )
    return UserMeResponse(
        id=user.id,
        username=user.username,
        email=user.email or None,
        first_name=user.first_name,
        last_name=user.last_name,
        social_providers=providers,
    )
