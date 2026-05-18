from contextlib import asynccontextmanager

from pathlib import Path

from django.conf import settings as django_settings
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .django_bridge import init_django

init_django()

from .routers import (  # noqa: E402
    assignments,
    attendance,
    auth_facebook,
    auth_github,
    auth_google,
    auth_otp,
    notifications,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_django()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="LMS: Auth, Attendance, Assignments, Notifications. Analytics on Django (port 8001).",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(auth_google.router)
app.include_router(auth_facebook.router)
app.include_router(auth_github.router)
app.include_router(auth_otp.router)
app.include_router(attendance.router)
app.include_router(assignments.router)
app.include_router(notifications.router)

_media_root = Path(django_settings.MEDIA_ROOT)
if _media_root.exists():
    app.mount("/media", StaticFiles(directory=str(_media_root)), name="media")


@app.get("/health")
def health():
    return {"status": "ok"}
