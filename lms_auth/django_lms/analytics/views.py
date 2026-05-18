from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from lms_core.models import Assignment, Attendance, Course, Enrollment, Submission


@require_GET
def dashboard(request):
    course_id = request.GET.get("course_id")
    if not course_id:
        return JsonResponse({"detail": "course_id query parameter is required"}, status=400)

    course = get_object_or_404(
        Course.objects.select_related("instructor"),
        pk=course_id,
    )

    enrollments = (
        Enrollment.objects.filter(course=course)
        .select_related("student")
        .prefetch_related("student__attendance_records")
    )
    total_students = enrollments.count()

    student_ids = list(enrollments.values_list("student_id", flat=True))
    attendance_qs = Attendance.objects.filter(course=course, student_id__in=student_ids)

    present_count = attendance_qs.filter(
        status__in=[Attendance.STATUS_PRESENT, Attendance.STATUS_LATE]
    ).count()
    total_records = attendance_qs.count()
    avg_attendance = round((present_count / total_records) * 100, 2) if total_records else 0.0

    assignment_stats = (
        Assignment.objects.filter(course=course)
        .annotate(submission_count=Count("submissions"))
        .aggregate(
            total_assignments=Count("id"),
            submissions_count=Count("submissions"),
        )
    )

    graded_count = (
        Submission.objects.filter(assignment__course=course, grade__isnull=False)
        .select_related("assignment", "student")
        .count()
    )

    return JsonResponse(
        {
            "course_id": course.id,
            "course_code": course.code,
            "course_title": course.title,
            "total_students": total_students,
            "avg_attendance": avg_attendance,
            "total_assignments": assignment_stats["total_assignments"] or 0,
            "submissions_count": assignment_stats["submissions_count"] or 0,
            "graded_submissions": graded_count,
        }
    )


@require_GET
def course_summary(request):
    """Extended metrics per course with ORM annotations."""
    course_id = request.GET.get("course_id")
    if not course_id:
        return JsonResponse({"detail": "course_id is required"}, status=400)

    course = get_object_or_404(Course, pk=course_id)

    per_student = (
        Enrollment.objects.filter(course=course)
        .select_related("student")
        .annotate(
            attendance_total=Count("student__attendance_records", filter=Q(student__attendance_records__course=course)),
            present_total=Count(
                "student__attendance_records",
                filter=Q(
                    student__attendance_records__course=course,
                    student__attendance_records__status__in=[
                        Attendance.STATUS_PRESENT,
                        Attendance.STATUS_LATE,
                    ],
                ),
            ),
            submission_total=Count("student__submissions", filter=Q(student__submissions__assignment__course=course)),
        )
        .values("student_id", "student__username", "attendance_total", "present_total", "submission_total")
    )

    students = []
    for row in per_student:
        total = row["attendance_total"]
        present = row["present_total"]
        pct = round((present / total) * 100, 2) if total else 0.0
        students.append(
            {
                "student_id": row["student_id"],
                "username": row["student__username"],
                "attendance_percentage": pct,
                "submissions_count": row["submission_total"],
            }
        )

    return JsonResponse({"course_id": course.id, "students": students})
