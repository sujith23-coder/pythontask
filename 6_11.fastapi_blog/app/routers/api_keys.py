import secrets

from django.db.models import Sum
from django.utils import timezone
from fastapi import APIRouter, Depends

from .. import schemas
from ..auth import get_current_user
from ..django_bridge import init_django
from ..models import User as SQLUser

DEFAULT_DAILY_LIMIT = 100
PLAN_DAILY_LIMITS = {
    "basic": 100,
    "pro": 500,
}

router = APIRouter(tags=["api key & usage"])


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


@router.post("/generate-key/", response_model=schemas.APIKeyResponse)
def generate_api_key(current: SQLUser = Depends(get_current_user)):
    init_django()
    from subscription.models import APIKey

    key_value = secrets.token_urlsafe(48)
    obj = APIKey.objects.filter(user_id=current.id).first()
    regenerated = obj is not None

    if obj:
        obj.key = key_value
        obj.save(update_fields=["key"])
    else:
        obj = APIKey.objects.create(user_id=current.id, key=key_value)

    return schemas.APIKeyResponse(api_key=obj.key, created_at=obj.created_at, regenerated=regenerated)


@router.get("/usage/", response_model=schemas.APIUsageSummaryResponse)
def get_usage(current: SQLUser = Depends(get_current_user)):
    init_django()
    from subscription.models import APIUsage

    qs = APIUsage.objects.filter(user_id=current.id)
    today = timezone.localdate()
    usage_rows = qs.order_by("-last_used")
    total = qs.aggregate(total=Sum("total_requests"))["total"] or 0
    daily = qs.filter(usage_date=today).aggregate(total=Sum("total_requests"))["total"] or 0
    limit = _resolve_daily_limit(current.id)

    usage = [
        schemas.APIUsageByEndpoint(endpoint=row.endpoint, total_requests=row.total_requests, last_used=row.last_used)
        for row in usage_rows
    ]
    return schemas.APIUsageSummaryResponse(
        total_requests=total,
        daily_requests=daily,
        daily_limit=limit,
        usage=usage,
    )
