from django.conf import settings
from django.db import models


class SocialAccount(models.Model):
    PROVIDER_GOOGLE = "google"
    PROVIDER_FACEBOOK = "facebook"
    PROVIDER_GITHUB = "github"
    PROVIDER_CHOICES = (
        (PROVIDER_GOOGLE, "Google"),
        (PROVIDER_FACEBOOK, "Facebook"),
        (PROVIDER_GITHUB, "GitHub"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    display_name = models.CharField(max_length=255, blank=True)
    avatar_url = models.URLField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_user_id"],
                name="unique_social_provider_account",
            )
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_user_id} -> {self.user.username}"


class OTPLog(models.Model):
    PURPOSE_LOGIN = "login"
    PURPOSE_SIGNUP = "signup"
    PURPOSE_CHOICES = (
        (PURPOSE_LOGIN, "Login"),
        (PURPOSE_SIGNUP, "Signup"),
    )

    identifier = models.CharField(
        max_length=255,
        help_text="Email address or phone number used for OTP",
    )
    otp_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default=PURPOSE_LOGIN)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="otp_logs",
    )
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "verified" if self.is_verified else "pending"
        return f"OTP {self.identifier} ({self.purpose}, {status})"
