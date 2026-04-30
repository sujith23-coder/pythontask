from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from .database import Base, engine
from .django_bridge import init_django
from .middleware import APIUsageMiddleware
from .models import Role
from .routers import admin_analytics, analytics, api_keys, auth, chat, email_router, posts, rbac, subscription


def _seed_default_roles() -> None:
    db = Session(bind=engine)
    try:
        for role_name in ("Admin", "Editor", "Viewer"):
            if not db.query(Role).filter(Role.name == role_name).first():
                db.add(Role(name=role_name))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_default_roles()
    init_django()
    yield


app = FastAPI(
    title="Blog & Subscription API",
    description="FastAPI blog (SQLAlchemy) + subscription/billing (Django ORM + ReportLab invoices). Task 6–7.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(APIUsageMiddleware)
app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(email_router.router)
app.include_router(subscription.router)
app.include_router(api_keys.router)
app.include_router(admin_analytics.router)
app.include_router(analytics.router)
app.include_router(rbac.router)
app.include_router(chat.router)
