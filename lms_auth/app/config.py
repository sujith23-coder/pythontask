import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LMS Authentication API"
    debug: bool = True

    jwt_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8000/auth/google/callback"

    facebook_client_id: str = ""
    facebook_client_secret: str = ""
    facebook_redirect_uri: str = "http://127.0.0.1:8000/auth/facebook/callback"

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://127.0.0.1:8000/auth/github/callback"

    otp_length: int = 6
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@lms.local"

    media_root: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
