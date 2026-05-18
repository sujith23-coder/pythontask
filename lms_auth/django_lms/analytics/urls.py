from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="analytics-dashboard"),
    path("course-summary/", views.course_summary, name="analytics-course-summary"),
]
