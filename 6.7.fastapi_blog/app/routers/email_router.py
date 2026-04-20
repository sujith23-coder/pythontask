from fastapi import APIRouter, BackgroundTasks, Depends, status

from .. import schemas
from ..auth import get_current_user
from ..models import User
from ..services.email import send_email_sync

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/send-notification/", status_code=status.HTTP_202_ACCEPTED)
def send_notification(
    payload: schemas.EmailNotificationRequest,
    background_tasks: BackgroundTasks,
    current: User = Depends(get_current_user),
):
    """
    Queue a notification email (demo / manual test).
    Comment and like flows also trigger emails via BackgroundTasks automatically.
    """
    background_tasks.add_task(
        send_email_sync,
        str(payload.to_email),
        payload.subject,
        payload.body,
    )
    return {"status": "queued", "detail": "Email will be sent in the background"}
