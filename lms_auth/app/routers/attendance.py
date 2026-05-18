from datetime import date

from django.db import IntegrityError, transaction
from fastapi import APIRouter, Depends, HTTPException, Query, status

from lms_core.models import Attendance

from ..auth_utils import get_current_user_id
from ..schemas_lms import (
    AttendanceEntryOut,
    AttendanceMarkRequest,
    AttendanceMarkResponse,
    CourseAttendanceOut,
    StudentAttendanceOut,
)
from ..services.notifications import notify_attendance_marked
from ..services.permissions import is_enrolled, require_course, require_instructor

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _serialize_record(record: Attendance) -> AttendanceEntryOut:
    return AttendanceEntryOut(
        id=record.id,
        course_id=record.course_id,
        student_id=record.student_id,
        student_username=record.student.username,
        date=record.date,
        status=record.status,
    )


def _attendance_percentage(records) -> tuple[int, int, float]:
    total = len(records)
    present = sum(1 for r in records if r.status in (Attendance.STATUS_PRESENT, Attendance.STATUS_LATE))
    pct = round((present / total) * 100, 2) if total else 0.0
    return total, present, pct


@router.post("/mark", response_model=AttendanceMarkResponse)
def mark_attendance(
    body: AttendanceMarkRequest,
    user_id: int = Depends(get_current_user_id),
):
    try:
        course = require_course(body.course_id)
        require_instructor(user_id, course)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    created = 0
    notifications_sent = 0

    try:
        with transaction.atomic():
            for item in body.records:
                if not is_enrolled(item.student_id, course.id):
                    raise ValueError(f"Student {item.student_id} is not enrolled in course {course.id}")

                if Attendance.objects.filter(
                    course=course, student_id=item.student_id, date=body.date
                ).exists():
                    raise ValueError(
                        f"Duplicate attendance for student {item.student_id} on {body.date}"
                    )

                Attendance.objects.create(
                    course=course,
                    student_id=item.student_id,
                    date=body.date,
                    status=item.status,
                    marked_by_id=user_id,
                )
                created += 1
                notify_attendance_marked(item.student_id, course, body.date, item.status)
                notifications_sent += 1
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate attendance entry for student/course/date",
        ) from exc

    return AttendanceMarkResponse(
        course_id=course.id,
        date=body.date,
        created=created,
        notifications_sent=notifications_sent,
    )


@router.get("/student/{student_id}", response_model=StudentAttendanceOut)
def get_student_attendance(
    student_id: int,
    course_id: int | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
):
    if user_id != student_id:
        try:
            if course_id:
                course = require_course(course_id)
                require_instructor(user_id, course)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="course_id is required when viewing another student's attendance",
                )
        except (ValueError, PermissionError) as exc:
            status_code = status.HTTP_403_FORBIDDEN if isinstance(exc, PermissionError) else status.HTTP_404_NOT_FOUND
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    qs = Attendance.objects.filter(student_id=student_id).select_related("student", "course")
    if course_id:
        qs = qs.filter(course_id=course_id)

    records = list(qs.order_by("-date"))
    total, present, pct = _attendance_percentage(records)

    return StudentAttendanceOut(
        student_id=student_id,
        course_id=course_id,
        total_days=total,
        present_days=present,
        attendance_percentage=pct,
        records=[_serialize_record(r) for r in records],
    )


@router.get("/course/{course_id}", response_model=CourseAttendanceOut)
def get_course_attendance(
    course_id: int,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    user_id: int = Depends(get_current_user_id),
):
    try:
        course = require_course(course_id)
        require_instructor(user_id, course)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    qs = Attendance.objects.filter(course=course).select_related("student", "course")
    if from_date:
        qs = qs.filter(date__gte=from_date)
    if to_date:
        qs = qs.filter(date__lte=to_date)

    records = list(qs.order_by("date", "student_id"))
    return CourseAttendanceOut(
        course_id=course_id,
        from_date=from_date,
        to_date=to_date,
        records=[_serialize_record(r) for r in records],
    )
