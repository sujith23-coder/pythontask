from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .django_bridge import init_django
from .routers import auth, email_router, posts, subscription


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    init_django()
    yield


app = FastAPI(
    title="Blog & Subscription API",
    description="FastAPI blog (SQLAlchemy) + subscription/billing (Django ORM + ReportLab invoices). Task 6–7.",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(email_router.router)
app.include_router(subscription.router)
