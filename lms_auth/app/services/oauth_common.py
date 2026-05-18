from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from ..auth_utils import create_access_token
from ..schemas import TokenResponse
from .users import get_or_create_user_from_social


def build_token_response(user, is_new_user: bool) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        username=user.username,
        email=user.email or None,
        is_new_user=is_new_user,
    )


async def exchange_code(
    token_url: str,
    data: dict,
    headers: dict | None = None,
) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(token_url, data=data, headers=headers or {})
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth token exchange failed: {response.text}",
        )
    return response.json()


async def fetch_json(url: str, headers: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers or {})
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch user profile: {response.text}",
        )
    return response.json()


def authorization_url(base: str, params: dict) -> str:
    return f"{base}?{urlencode(params)}"
