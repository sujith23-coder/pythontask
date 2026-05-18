from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AttendanceRecordIn(BaseModel):
    student_id: int
    status: str = Field(..., pattern="^(Present|Absent|Late)$")


class AttendanceMarkRequest(BaseModel):
    course_id: int
    date: date
    records: list[AttendanceRecordIn]


class AttendanceMarkResponse(BaseModel):
    course_id: int
    date: date
    created: int
    notifications_sent: int


class AttendanceEntryOut(BaseModel):
    id: int
    course_id: int
    student_id: int
    student_username: str
    date: date
    status: str


class StudentAttendanceOut(BaseModel):
    student_id: int
    course_id: int | None
    total_days: int
    present_days: int
    attendance_percentage: float
    records: list[AttendanceEntryOut]


class CourseAttendanceOut(BaseModel):
    course_id: int
    from_date: date | None
    to_date: date | None
    records: list[AttendanceEntryOut]


class AssignmentOut(BaseModel):
    id: int
    course_id: int
    title: str
    description: str
    deadline: datetime
    file_url: str | None
    created_by_id: int


class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    file_url: str
    version: int
    submitted_at: datetime
    grade: Decimal | None
    remarks: str


class GradeSubmissionRequest(BaseModel):
    submission_id: int
    grade: Decimal = Field(..., ge=0, le=100)
    remarks: str = ""


class NotificationOut(BaseModel):
    id: int
    user_id: int
    message: str
    link: str
    is_read: bool
    created_at: datetime


class MarkReadRequest(BaseModel):
    notification_ids: list[int] = Field(default_factory=list)
    mark_all: bool = False
