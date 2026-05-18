from fastapi import APIRouter, HTTPException, Query, status

from accounts.models import SocialAccount

from ..config import get_settings
from ..schemas import OAuthCallbackRequest, OAuthLoginResponse, TokenResponse
from ..services.oauth_common import authorization_url, build_token_response, exchange_code, fetch_json
from ..services.oauth_state import create_state, validate_state
from ..services.users import get_or_create_user_from_social

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/login", response_model=OAuthLoginResponse)
def google_login():
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    state = create_state(SocialAccount.PROVIDER_GOOGLE)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return OAuthLoginResponse(
        authorization_url=authorization_url(GOOGLE_AUTH_URL, params),
        state=state,
    )


@router.get("/callback", response_model=TokenResponse)
async def google_callback(
    code: str = Query(...),
    state: str | None = Query(default=None),
):
    if not validate_state(state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
    return await _complete_google_oauth(code)


@router.post("/callback", response_model=TokenResponse)
async def google_callback_post(body: OAuthCallbackRequest):
    if body.state and not validate_state(body.state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
    return await _complete_google_oauth(body.code)


async def _complete_google_oauth(code: str) -> TokenResponse:
    settings = get_settings()
    token_data = await exchange_code(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token from Google")

    profile = await fetch_json(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    provider_user_id = str(profile.get("id", ""))
    if not provider_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google profile missing user id")

    user, _, is_new = get_or_create_user_from_social(
        provider=SocialAccount.PROVIDER_GOOGLE,
        provider_user_id=provider_user_id,
        email=profile.get("email"),
        display_name=profile.get("name"),
        avatar_url=profile.get("picture", ""),
        extra_data=profile,
    )
    return build_token_response(user, is_new)
