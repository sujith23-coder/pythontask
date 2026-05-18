from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import OTPLog, SocialAccount


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "provider", "provider_user_id", "email", "created_at")
    list_filter = ("provider", "created_at")
    search_fields = ("provider_user_id", "email", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user",)


@admin.register(OTPLog)
class OTPLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "identifier",
        "purpose",
        "is_verified",
        "attempts",
        "expires_at",
        "created_at",
    )
    list_filter = ("purpose", "is_verified", "created_at")
    search_fields = ("identifier", "user__username", "user__email")
    readonly_fields = ("otp_hash", "created_at", "verified_at")
    raw_id_fields = ("user",)


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "is_staff", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
