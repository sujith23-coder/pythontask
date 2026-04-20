import uuid
from datetime import timedelta

from django.utils import timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from .. import schemas
from ..auth import get_current_user
from ..django_bridge import init_django
from ..models import User as SQLUser
from ..services.email import send_email_sync
from ..services.invoice_pdf import generate_invoice_pdf

router = APIRouter(tags=["subscription & billing"])


def _billing_to_read(bh) -> schemas.BillingHistoryRead:
    p = bh.plan
    return schemas.BillingHistoryRead(
        id=bh.id,
        plan=schemas.SubscriptionPlanRead(
            id=p.id,
            name=p.name,
            price=p.price,
            duration=p.duration,
        ),
        start_date=bh.start_date,
        end_date=bh.end_date,
        invoice=bh.invoice,
        transaction_id=bh.transaction_id or f"TXN-{bh.id:06d}",
    )


def _subscribe_email_task(to_email: str, subject: str, body: str) -> None:
    send_email_sync(to_email, subject, body)


@router.post("/subscribe/", response_model=schemas.SubscribeResponse, status_code=status.HTTP_201_CREATED)
def subscribe(
    data: schemas.SubscribeRequest,
    background_tasks: BackgroundTasks,
    current: SQLUser = Depends(get_current_user),
):
    """
    Subscribe to a plan (Django ORM). Creates billing row, generates ReportLab PDF invoice.
    """
    init_django()
    from subscription.models import BillingHistory, BlogUser, SubscriptionPlan

    plan = SubscriptionPlan.objects.filter(pk=data.plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    if not BlogUser.objects.filter(pk=current.id).exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User record missing in database")

    user_dj = BlogUser.objects.get(pk=current.id)
    start = timezone.now()
    end = start + timedelta(days=plan.duration)
    txn = f"TXN-{uuid.uuid4().hex[:12].upper()}"

    bh = BillingHistory(
        user=user_dj,
        plan=plan,
        start_date=start,
        end_date=end,
        invoice="",
        transaction_id=txn,
    )
    bh.save()

    pdf_path = generate_invoice_pdf(
        billing_id=bh.id,
        customer_name=current.username,
        plan_name=plan.name,
        price_inr=plan.price,
        start_date=start,
        end_date=end,
        transaction_id=txn,
    )
    bh.invoice = pdf_path
    bh.save(update_fields=["invoice"])

    background_tasks.add_task(
        _subscribe_email_task,
        current.email,
        f"Subscription confirmed: {plan.name}",
        f"Hi {current.username},\n\nYour plan '{plan.name}' is active until {end.isoformat()}.\n"
        f"Transaction: {txn}\nInvoice: {pdf_path}\n",
    )

    return schemas.SubscribeResponse(
        message="Subscribed successfully",
        billing=_billing_to_read(bh),
    )


@router.get("/subscription/me", response_model=schemas.ActiveSubscriptionResponse)
def get_my_subscription(current: SQLUser = Depends(get_current_user)):
    """Latest subscription that is still active (end_date >= now)."""
    init_django()
    from subscription.models import BillingHistory

    now = timezone.now()
    bh = (
        BillingHistory.objects.filter(user_id=current.id, end_date__gte=now)
        .select_related("plan")
        .order_by("-start_date")
        .first()
    )
    if not bh:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription")
    return schemas.ActiveSubscriptionResponse(billing=_billing_to_read(bh))


@router.get("/billing/history", response_model=list[schemas.BillingHistoryRead])
def billing_history(current: SQLUser = Depends(get_current_user)):
    init_django()
    from subscription.models import BillingHistory

    rows = BillingHistory.objects.filter(user_id=current.id).select_related("plan").order_by("-start_date")
    return [_billing_to_read(bh) for bh in rows]
