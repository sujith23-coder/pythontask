from django.db.models import Sum
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_roles
from ..database import get_db
from ..models import User
from .admin_analytics import _plan_distribution
from ..django_bridge import init_django

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary/", response_model=schemas.AnalyticsSummaryV2Response)
def analytics_summary(_: User = Depends(require_roles("Admin")), db: Session = Depends(get_db)):
    init_django()
    from subscription.models import APIUsage

    total_users = db.query(User).count()
    total_calls = APIUsage.objects.aggregate(total=Sum("total_requests"))["total"] or 0
    active_users = (
        APIUsage.objects.values("user_id")
        .annotate(requests=Sum("total_requests"))
        .filter(requests__gt=0)
        .count()
    )
    return schemas.AnalyticsSummaryV2Response(
        total_users=int(total_users),
        total_api_calls=int(total_calls),
        active_users=int(active_users),
    )


@router.get("/top-users/", response_model=list[schemas.TopUserAnalytics])
def analytics_top_users(_: User = Depends(require_roles("Admin"))):
    init_django()
    from subscription.models import APIUsage, BlogUser

    top_rows = (
        APIUsage.objects.values("user_id")
        .annotate(requests=Sum("total_requests"))
        .order_by("-requests")[:5]
    )
    user_ids = [row["user_id"] for row in top_rows]
    users_by_id = BlogUser.objects.in_bulk(user_ids)
    return [
        schemas.TopUserAnalytics(
            user=(users_by_id[row["user_id"]].email if row["user_id"] in users_by_id else f"user-{row['user_id']}"),
            requests=int(row["requests"] or 0),
        )
        for row in top_rows
    ]


@router.get("/plan-distribution/", response_model=dict[str, int])
def analytics_plan_distribution(_: User = Depends(require_roles("Admin"))):
    return _plan_distribution()
