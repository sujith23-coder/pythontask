from fastapi import APIRouter, HTTPException, Query, status

from accounts.models import SocialAccount

from ..config import get_settings
from ..schemas import OAuthCallbackRequest, OAuthLoginResponse, TokenResponse
from ..services.oauth_common import authorization_url, build_token_response, exchange_code, fetch_json
from ..services.oauth_state import create_state, validate_state
from ..services.users import get_or_create_user_from_social

router = APIRouter(prefix="/auth/github", tags=["GitHub OAuth"])

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


@router.get("/login", response_model=OAuthLoginResponse)
def github_login():
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.",
        )
    state = create_state(SocialAccount.PROVIDER_GITHUB)
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user user:email",
        "state": state,
    }
    return OAuthLoginResponse(
        authorization_url=authorization_url(GITHUB_AUTH_URL, params),
        state=state,
    )


@router.get("/callback", response_model=TokenResponse)
async def github_callback(
    code: str = Query(...),
    state: str | None = Query(default=None),
):
    if not validate_state(state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
    return await _complete_github_oauth(code)


@router.post("/callback", response_model=TokenResponse)
async def github_callback_post(body: OAuthCallbackRequest):
    if body.state and not validate_state(body.state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")
    return await _complete_github_oauth(body.code)


async def _complete_github_oauth(code: str) -> TokenResponse:
    settings = get_settings()
    token_data = await exchange_code(
        GITHUB_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "redirect_uri": settings.github_redirect_uri,
        },
        headers={"Accept": "application/json"},
    )
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token from GitHub")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    profile = await fetch_json(GITHUB_USER_URL, headers=headers)
    provider_user_id = str(profile.get("id", ""))
    if not provider_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub profile missing user id")

    email = profile.get("email")
    if not email:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            emails_resp = await client.get(GITHUB_EMAILS_URL, headers=headers)
        if emails_resp.status_code < 400:
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary")), None)
            email = (primary or (emails[0] if emails else {})).get("email")

    user, _, is_new = get_or_create_user_from_social(
        provider=SocialAccount.PROVIDER_GITHUB,
        provider_user_id=provider_user_id,
        email=email,
        display_name=profile.get("name") or profile.get("login"),
        avatar_url=profile.get("avatar_url", ""),
        extra_data=profile,
    )
    return build_token_response(user, is_new)
