from datetime import datetime, timezone
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db.models import Max
from django.utils import timezone as dj_timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from lms_core.models import Assignment, Submission

from ..auth_utils import get_current_user_id
from ..schemas_lms import AssignmentOut, GradeSubmissionRequest, SubmissionOut
from ..services.notifications import notify_assignment_created, notify_assignment_graded
from ..services.permissions import is_course_instructor, require_course, require_enrolled, require_instructor

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def _file_url(file_field) -> str | None:
    if file_field and hasattr(file_field, "url"):
        return file_field.url
    return None


def _assignment_out(assignment: Assignment) -> AssignmentOut:
    return AssignmentOut(
        id=assignment.id,
        course_id=assignment.course_id,
        title=assignment.title,
        description=assignment.description,
        deadline=assignment.deadline,
        file_url=_file_url(assignment.attachment),
        created_by_id=assignment.created_by_id,
    )


def _submission_out(submission: Submission) -> SubmissionOut:
    return SubmissionOut(
        id=submission.id,
        assignment_id=submission.assignment_id,
        student_id=submission.student_id,
        file_url=_file_url(submission.file) or "",
        version=submission.version,
        submitted_at=submission.submitted_at,
        grade=submission.grade,
        remarks=submission.remarks or "",
    )


@router.post("/create", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    title: str = Form(...),
    description: str = Form(""),
    deadline: datetime = Form(...),
    course_id: int = Form(...),
    file: UploadFile | None = File(default=None),
    user_id: int = Depends(get_current_user_id),
):
    try:
        course = require_course(course_id)
        require_instructor(user_id, course)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    assignment = Assignment(
        course=course,
        title=title,
        description=description,
        deadline=deadline,
        created_by_id=user_id,
    )
    assignment.save()
    if file and file.filename:
        content = await file.read()
        assignment.attachment.save(file.filename, ContentFile(content), save=True)

    notify_assignment_created(assignment)
    return _assignment_out(assignment)


@router.post("/submit", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    assignment_id: int = Form(...),
    student_id: int = Form(...),
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
):
    if user_id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot submit for another student")

    assignment = (
        Assignment.objects.select_related("course")
        .filter(id=assignment_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    try:
        require_enrolled(student_id, assignment.course_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    now = dj_timezone.now()
    if now > assignment.deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission deadline has passed",
        )

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is required")

    latest_version = (
        Submission.objects.filter(assignment=assignment, student_id=student_id)
        .aggregate(max_v=Max("version"))
        .get("max_v")
    ) or 0
    new_version = latest_version + 1

    content = await file.read()
    submission = Submission(
        assignment=assignment,
        student_id=student_id,
        version=new_version,
    )
    submission.save()
    submission.file.save(file.filename, ContentFile(content), save=True)

    return _submission_out(submission)


@router.put("/grade", response_model=SubmissionOut)
def grade_submission(
    body: GradeSubmissionRequest,
    user_id: int = Depends(get_current_user_id),
):
    submission = (
        Submission.objects.select_related("assignment__course", "student")
        .filter(id=body.submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    course = submission.assignment.course
    try:
        require_instructor(user_id, course)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    submission.grade = Decimal(str(body.grade))
    submission.remarks = body.remarks
    submission.graded_by_id = user_id
    submission.graded_at = dj_timezone.now()
    submission.save()

    notify_assignment_graded(submission)
    return _submission_out(submission)


@router.get("/course/{course_id}", response_model=list[AssignmentOut])
def list_course_assignments(
    course_id: int,
    user_id: int = Depends(get_current_user_id),
):
    try:
        course = require_course(course_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if not is_course_instructor(user_id, course):
        try:
            require_enrolled(user_id, course_id)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    assignments = Assignment.objects.filter(course=course).select_related("course", "created_by")
    return [_assignment_out(a) for a in assignments]
