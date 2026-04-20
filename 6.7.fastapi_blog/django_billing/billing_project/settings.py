"""
Django settings for subscription/billing models only.
Uses the same SQLite file as the FastAPI blog (blog.db).
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FASTAPI_ROOT = BASE_DIR.parent

SECRET_KEY = "django-billing-task7-dev-not-for-production"
DEBUG = True
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "subscription",
]

MIDDLEWARE: list = []

ROOT_URLCONF = "billing_project.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(FASTAPI_ROOT / "blog.db"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
