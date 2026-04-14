from django.urls import path

from .views import (
    change_password_view,
    login_view,
    logout_view,
    profile_view,
    signup_view,
    update_profile_view,
    upload_profile_photo_view,
)

urlpatterns = [
    path("signup/", signup_view, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("profile/", profile_view, name="profile"),
    path("profile/update/", update_profile_view, name="profile_update"),
    path("change-password/", change_password_view, name="change_password"),
    path("profile/photo/", upload_profile_photo_view, name="profile_photo"),
]
