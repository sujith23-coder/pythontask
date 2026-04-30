"""Smoke test for Task 10 admin analytics + dashboard endpoints."""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "billing_project.settings")

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

Base.metadata.create_all(bind=engine)

sys.path.insert(0, os.path.join(ROOT, "django_billing"))
import django
from django.core.management import call_command

django.setup()
call_command("migrate", "--noinput", verbosity=0)

c = TestClient(app)

username = f"task10_admin_{int(time.time())}"
email = f"{username}@example.com"
password = "password123"

r = c.post("/auth/register", json={"username": username, "email": email, "password": password})
assert r.status_code == 201, r.text

t = c.post("/auth/login", data={"username": username, "password": password})
assert t.status_code == 200, t.text
token = t.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

g = c.post("/generate-key/", headers=h)
assert g.status_code == 200, g.text
api_key = g.json()["api_key"]
h_api = {"Authorization": f"Bearer {token}", "X-API-Key": api_key}

# Generate at least one tracked request so analytics has data for this user.
mine = c.get("/posts/mine", headers=h_api)
assert mine.status_code == 200, mine.text

summary = c.get("/admin/analytics/summary", headers=h_api)
assert summary.status_code == 200, summary.text
summary_data = summary.json()
for key in ("total_users", "total_requests", "top_users", "plan_distribution"):
    assert key in summary_data, summary_data

daily = c.get("/admin/analytics/usage-daily", headers=h_api)
assert daily.status_code == 200, daily.text
daily_data = daily.json()
assert "daily_usage" in daily_data and len(daily_data["daily_usage"]) == 7, daily_data

dashboard = c.get("/admin/analytics/dashboard")
assert dashboard.status_code == 200, dashboard.text
assert "Dashboard - Admin Analytics" in dashboard.text

print("task10 analytics ok")
print("summary:", summary_data)
print("daily_usage:", daily_data["daily_usage"])
