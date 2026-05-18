from django.contrib.auth.models import User

from lms_core.models import Course, Enrollment


def get_user(user_id: int) -> User:
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise ValueError("User not found")
    return user


def require_course(course_id: int) -> Course:
    course = Course.objects.filter(id=course_id, is_active=True).select_related("instructor").first()
    if not course:
        raise ValueError("Course not found or inactive")
    return course


def is_course_instructor(user_id: int, course: Course) -> bool:
    user = get_user(user_id)
    return user.is_staff or course.instructor_id == user_id


def is_enrolled(student_id: int, course_id: int) -> bool:
    return Enrollment.objects.filter(course_id=course_id, student_id=student_id).exists()


def require_instructor(user_id: int, course: Course) -> None:
    if not is_course_instructor(user_id, course):
        raise PermissionError("Only the course instructor can perform this action")


def require_enrolled(student_id: int, course_id: int) -> None:
    if not is_enrolled(student_id, course_id):
        raise PermissionError("Student is not enrolled in this course")
