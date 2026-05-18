from fastapi import APIRouter, HTTPException, Query, status

from accounts.models import SocialAccount

from ..config import get_settings
from ..schemas import OAuthCallbackRequest, OAuthLoginResponse, TokenResponse
import httpx

from ..services.oauth_common import authorization_url, build_token_response, exchange_code
from ..services.oauth_state import create_state, validate_state
from ..services.users import get_or_create_user_from_social

router = APIRouter(prefix="/auth/facebook", tags=["Facebook OAuth"])

FACEBOOK_AUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
FACEBOOK_PROFILE_URL = "https://graph.facebook.com/me"


@router.get("/login", response_model=OAuthLoginResponse)
def facebook_login():
    settings = get_settings()
    if not settings.facebook_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Facebook OAuth is not configured. Set FACEBOOK_CLIENT_ID and FACEBOOK_CLIENT_SECRET.",
        )
    state = create_state(SocialAccount.PROVIDER_FACEBOOK)
    params = {
        "client_id": settings.facebook_client_id,
        "redirect_uri": settings.facebook_redirect_uri,
        "response_type": "code",
        "scope": "email,public_profile",
        "state": state,
    }
    return OAuthLoginResponse(
        authorization_url=authorization_url(FACEBOOK_AUTH_URL, params),
        state=state,
    )


@router.get("/callback", response_model=TokenResponse)
async def facebook_callback(
    code: str = Query(...),
    state: str | None = Query(default=None),
):
    if not validate_state(state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
    return await _complete_facebook_oauth(code)


@router.post("/callback", response_model=TokenResponse)
async def facebook_callback_post(body: OAuthCallbackRequest):
    if body.state and not validate_state(body.state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
    return await _complete_facebook_oauth(body.code)


async def _complete_facebook_oauth(code: str) -> TokenResponse:
    settings = get_settings()
    token_data = await exchange_code(
        FACEBOOK_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.facebook_client_id,
            "client_secret": settings.facebook_client_secret,
            "redirect_uri": settings.facebook_redirect_uri,
        },
    )
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token from Facebook")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            FACEBOOK_PROFILE_URL,
            params={"fields": "id,name,email,picture", "access_token": access_token},
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch Facebook profile: {response.text}",
        )
    profile = response.json()

    provider_user_id = str(profile.get("id", ""))
    if not provider_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Facebook profile missing user id")

    picture = ""
    if isinstance(profile.get("picture"), dict):
        picture = profile["picture"].get("data", {}).get("url", "")

    user, _, is_new = get_or_create_user_from_social(
        provider=SocialAccount.PROVIDER_FACEBOOK,
        provider_user_id=provider_user_id,
        email=profile.get("email"),
        display_name=profile.get("name"),
        avatar_url=picture,
        extra_data=profile,
    )
    return build_token_response(user, is_new)
