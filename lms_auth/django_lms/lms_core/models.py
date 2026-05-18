from django.conf import settings
from django.db import models


class Course(models.Model):
    code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses_taught",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.title}"


class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "student"], name="unique_course_enrollment")
        ]

    def __str__(self):
        return f"{self.student.username} in {self.course.code}"


class Attendance(models.Model):
    STATUS_PRESENT = "Present"
    STATUS_ABSENT = "Absent"
    STATUS_LATE = "Late"
    STATUS_CHOICES = (
        (STATUS_PRESENT, "Present"),
        (STATUS_ABSENT, "Absent"),
        (STATUS_LATE, "Late"),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attendance_records")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="attendance_marked",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "student_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "student", "date"],
                name="unique_attendance_per_day",
            )
        ]

    def __str__(self):
        return f"{self.student.username} {self.course.code} {self.date} {self.status}"


def assignment_upload_path(instance, filename):
    return f"assignments/course_{instance.course_id}/{filename}"


def submission_upload_path(instance, filename):
    return f"submissions/assignment_{instance.assignment_id}/student_{instance.student_id}/v{instance.version}_{filename}"


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    deadline = models.DateTimeField()
    attachment = models.FileField(upload_to=assignment_upload_path, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.course.code})"


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    file = models.FileField(upload_to=submission_upload_path)
    version = models.PositiveSmallIntegerField(default=1)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions_graded",
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student", "version"],
                name="unique_submission_version",
            )
        ]

    def __str__(self):
        return f"{self.student.username} -> {self.assignment.title} v{self.version}"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.TextField()
    link = models.CharField(max_length=512, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:40]}"
