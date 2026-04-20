"""Create SQLAlchemy tables, ensure Django migrations, then test subscription API."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "billing_project.settings")

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

# Fresh DB optional — comment out to reuse
# if os.path.exists(os.path.join(ROOT, "blog.db")):
#     os.remove(os.path.join(ROOT, "blog.db"))

Base.metadata.create_all(bind=engine)

sys.path.insert(0, os.path.join(ROOT, "django_billing"))
import django
from django.core.management import call_command

django.setup()
call_command("migrate", "--noinput", verbosity=0)

c = TestClient(app)
r = c.post(
    "/auth/register",
    json={"username": "subscriber", "email": "sub@example.com", "password": "password123"},
)
assert r.status_code == 201, r.text
t = c.post("/auth/login", data={"username": "subscriber", "password": "password123"})
assert t.status_code == 200, t.text
token = t.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}
sub = c.post("/subscribe/", headers=h, json={"plan_id": 1})
assert sub.status_code == 201, sub.text
data = sub.json()
assert "invoice" in data["billing"] and data["billing"]["invoice"].endswith(".pdf")
me = c.get("/subscription/me", headers=h)
assert me.status_code == 200
hist = c.get("/billing/history", headers=h)
assert len(hist.json()) >= 1
print("task7 billing ok:", data["billing"]["invoice"])
