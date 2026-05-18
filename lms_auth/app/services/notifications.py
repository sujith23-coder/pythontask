import logging
import smtplib
from email.message import EmailMessage

from django.contrib.auth.models import User

from lms_core.models import Notification

from ..config import get_settings

logger = logging.getLogger(__name__)


def create_notification(user_id: int, message: str, link: str = "") -> Notification:
    return Notification.objects.create(user_id=user_id, message=message, link=link)


def notify_users(user_ids: list[int], message: str, link: str = "") -> int:
    rows = [Notification(user_id=uid, message=message, link=link) for uid in user_ids]
    Notification.objects.bulk_create(rows)
    return len(rows)


def notify_assignment_created(assignment) -> int:
    from lms_core.models import Enrollment

    student_ids = list(
        Enrollment.objects.filter(course=assignment.course).values_list("student_id", flat=True)
    )
    link = f"/assignments/{assignment.id}"
    message = f"New assignment: {assignment.title} (due {assignment.deadline:%Y-%m-%d %H:%M})"
    count = notify_users(student_ids, message, link)
    _maybe_email_faculty(assignment.created_by_id, message)
    return count


def notify_assignment_graded(submission) -> Notification:
    link = f"/assignments/{submission.assignment_id}/submissions/{submission.id}"
    message = f"Your submission for '{submission.assignment.title}' was graded: {submission.grade}"
    return create_notification(submission.student_id, message, link)


def notify_attendance_marked(student_id: int, course, date, status: str) -> Notification:
    link = f"/attendance/student/{student_id}?course_id={course.id}"
    message = f"Attendance marked for {course.code} on {date}: {status}"
    return create_notification(student_id, message, link)


def _maybe_email_faculty(user_id: int, message: str) -> None:
    settings = get_settings()
    if not (settings.smtp_host and settings.smtp_user):
        return
    user = User.objects.filter(id=user_id).first()
    if not user or not user.email:
        return
    if not (user.is_staff or user.courses_taught.exists()):
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = "LMS notification"
        msg["From"] = settings.smtp_from_email
        msg["To"] = user.email
        msg.set_content(message)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception as exc:
        logger.warning("Failed to send faculty email: %s", exc)
