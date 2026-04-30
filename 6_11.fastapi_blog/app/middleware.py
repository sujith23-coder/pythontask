from __future__ import annotations

from asgiref.sync import sync_to_async
from django.db.models import F, Sum
from django.utils import timezone
from fastapi import status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import decode_token
from .django_bridge import init_django

DEFAULT_DAILY_LIMIT = 100
PLAN_DAILY_LIMITS = {
    "basic": 100,
    "pro": 500,
}
EXEMPT_PATH_PREFIXES = ("/docs", "/openapi.json", "/redoc", "/auth/", "/generate-key/", "/usage/")


def _resolve_daily_limit(user_id: int) -> int:
    from subscription.models import BillingHistory

    now = timezone.now()
    active = (
        BillingHistory.objects.filter(user_id=user_id, end_date__gte=now)
        .select_related("plan")
        .order_by("-start_date")
        .first()
    )
    if not active:
        return DEFAULT_DAILY_LIMIT
    return PLAN_DAILY_LIMITS.get(active.plan.name.strip().lower(), DEFAULT_DAILY_LIMIT)


class APIUsageMiddleware(BaseHTTPMiddleware):
    @staticmethod
    def _validate_request(user_id: int, api_key: str) -> tuple[bool, str | None]:
        init_django()
        from subscription.models import APIKey, APIUsage

        if not APIKey.objects.filter(user_id=user_id, key=api_key).exists():
            return False, "Invalid API key"

        today = timezone.localdate()
        daily_limit = _resolve_daily_limit(user_id)
        today_total = (
            APIUsage.objects.filter(user_id=user_id, usage_date=today).aggregate(total=Sum("total_requests"))["total"] or 0
        )
        if today_total >= daily_limit:
            return False, f"Daily API request limit exceeded ({daily_limit}/day)"
        return True, None

    @staticmethod
    def _record_usage(user_id: int, path: str) -> None:
        init_django()
        from subscription.models import APIUsage

        now = timezone.now()
        today = timezone.localdate()
        APIUsage.objects.update_or_create(
            user_id=user_id,
            endpoint=path,
            usage_date=today,
            defaults={"last_used": now},
        )
        APIUsage.objects.filter(user_id=user_id, endpoint=path, usage_date=today).update(
            total_requests=F("total_requests") + 1,
            last_used=now,
        )

    async def dispatch(self, request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or path.startswith(EXEMPT_PATH_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header.split(" ", 1)[1].strip()
        try:
            user_id = int(decode_token(token))
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
            )

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "X-API-Key header required"},
            )

        valid, error = await sync_to_async(self._validate_request, thread_sensitive=True)(user_id, api_key)
        if not valid and error == "Invalid API key":
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": error},
            )
        if not valid:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": error},
            )

        response = await call_next(request)
        await sync_to_async(self._record_usage, thread_sensitive=True)(user_id, path)
        return response
