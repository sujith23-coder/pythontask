from django.contrib import admin

from .models import Assignment, Attendance, Course, Enrollment, Notification, Submission


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "title", "instructor", "is_active", "created_at")
    search_fields = ("code", "title", "instructor__username")
    list_filter = ("is_active",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "student", "enrolled_at")
    list_filter = ("course",)
    raw_id_fields = ("course", "student")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "student", "date", "status", "marked_by")
    list_filter = ("course", "status", "date")
    raw_id_fields = ("course", "student", "marked_by")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "course", "deadline", "created_by", "created_at")
    list_filter = ("course",)
    raw_id_fields = ("course", "created_by")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "assignment", "student", "version", "grade", "submitted_at")
    list_filter = ("assignment__course",)
    raw_id_fields = ("assignment", "student", "graded_by")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "message", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("message", "user__username")
    raw_id_fields = ("user",)
