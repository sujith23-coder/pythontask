from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from lms_core.models import Assignment, Course, Enrollment


class Command(BaseCommand):
    help = "Load sample faculty, students, courses, and enrollments for LMS testing"

    def handle(self, *args, **options):
        faculty, _ = User.objects.get_or_create(
            username="faculty1",
            defaults={"email": "faculty1@lms.local", "first_name": "Jane", "last_name": "Instructor"},
        )
        if not faculty.has_usable_password():
            faculty.set_password("faculty123")
            faculty.save()

        students = []
        for i in range(1, 4):
            student, _ = User.objects.get_or_create(
                username=f"student{i}",
                defaults={"email": f"student{i}@lms.local"},
            )
            if not student.has_usable_password():
                student.set_password("student123")
                student.save()
            students.append(student)

        course, _ = Course.objects.get_or_create(
            code="CS101",
            defaults={
                "title": "Introduction to Programming",
                "description": "Sample course for LMS advanced features",
                "instructor": faculty,
            },
        )
        if course.instructor_id != faculty.id:
            course.instructor = faculty
            course.save()

        for student in students:
            Enrollment.objects.get_or_create(course=course, student=student)

        Assignment.objects.get_or_create(
            course=course,
            title="Hello World Lab",
            defaults={
                "description": "Submit your first program",
                "deadline": timezone.now() + timedelta(days=14),
                "created_by": faculty,
            },
        )

        self.stdout.write(self.style.SUCCESS("Sample data loaded."))
        self.stdout.write(f"  Faculty: {faculty.username} / faculty123 (id={faculty.id})")
        for s in students:
            self.stdout.write(f"  Student: {s.username} / student123 (id={s.id})")
        self.stdout.write(f"  Course: {course.code} (id={course.id})")
