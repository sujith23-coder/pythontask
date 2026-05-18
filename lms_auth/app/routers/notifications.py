from fastapi import APIRouter, Depends, HTTPException, status

from lms_core.models import Notification

from ..auth_utils import get_current_user_id
from ..schemas_lms import MarkReadRequest, NotificationOut

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _serialize(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        user_id=n.user_id,
        message=n.message,
        link=n.link,
        is_read=n.is_read,
        created_at=n.created_at,
    )


@router.get("/{user_id}", response_model=list[NotificationOut])
def list_notifications(
    user_id: int,
    unread_only: bool = False,
    current_user_id: int = Depends(get_current_user_id),
):
    if current_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view another user's notifications")

    qs = Notification.objects.filter(user_id=user_id)
    if unread_only:
        qs = qs.filter(is_read=False)
    return [_serialize(n) for n in qs.order_by("-created_at")[:100]]


@router.post("/mark-read")
def mark_notifications_read(
    body: MarkReadRequest,
    current_user_id: int = Depends(get_current_user_id),
):
    if body.mark_all:
        updated = Notification.objects.filter(user_id=current_user_id, is_read=False).update(is_read=True)
        return {"updated": updated}

    if not body.notification_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide notification_ids or mark_all=true")

    updated = Notification.objects.filter(
        user_id=current_user_id,
        id__in=body.notification_ids,
    ).update(is_read=True)
    return {"updated": updated}
