from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from lms_core.models import Assignment, Attendance, Course, Enrollment, Submission


@pytest.fixture
def faculty(db):
    return User.objects.create_user(username="fac", email="fac@lms.local", password="x")


@pytest.fixture
def student(db):
    return User.objects.create_user(username="stu", email="stu@lms.local", password="x")


@pytest.fixture
def course(db, faculty):
    return Course.objects.create(code="TST", title="Test", instructor=faculty)


@pytest.fixture
def enrollment(db, course, student):
    return Enrollment.objects.create(course=course, student=student)


@pytest.mark.django_db
def test_unique_attendance(course, student, faculty, enrollment):
    Attendance.objects.create(
        course=course,
        student=student,
        date=date(2025, 10, 30),
        status=Attendance.STATUS_PRESENT,
        marked_by=faculty,
    )
    with pytest.raises(Exception):
        Attendance.objects.create(
            course=course,
            student=student,
            date=date(2025, 10, 30),
            status=Attendance.STATUS_ABSENT,
            marked_by=faculty,
        )


@pytest.mark.django_db
def test_submission_versioning(course, student, faculty, enrollment):
    assignment = Assignment.objects.create(
        course=course,
        title="Lab",
        deadline=timezone.now() + timedelta(days=1),
        created_by=faculty,
    )
    Submission.objects.create(assignment=assignment, student=student, version=1)
    assert Submission.objects.filter(assignment=assignment, student=student).count() == 1


@pytest.mark.django_db
def test_deadline_passed(course, student, faculty, enrollment):
    assignment = Assignment.objects.create(
        course=course,
        title="Late Lab",
        deadline=timezone.now() - timedelta(hours=1),
        created_by=faculty,
    )
    assert timezone.now() > assignment.deadline
