"""Smoke test for Task 11: RBAC + analytics + chat API basics."""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "billing_project.settings")

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.models import Role, UserRole
from sqlalchemy.orm import Session

Base.metadata.create_all(bind=engine)

sys.path.insert(0, os.path.join(ROOT, "django_billing"))
import django
from django.core.management import call_command

django.setup()
call_command("migrate", "--noinput", verbosity=0)

c = TestClient(app)
seed = int(time.time())

# First user becomes Admin automatically.
admin_u = f"admin_{seed}"
viewer_u = f"viewer_{seed}"
password = "password123"

r1 = c.post("/auth/register", json={"username": admin_u, "email": f"{admin_u}@example.com", "password": password})
assert r1.status_code == 201, r1.text
r2 = c.post("/auth/register", json={"username": viewer_u, "email": f"{viewer_u}@example.com", "password": password})
assert r2.status_code == 201, r2.text

t_admin = c.post("/auth/login", data={"username": admin_u, "password": password})
t_viewer = c.post("/auth/login", data={"username": viewer_u, "password": password})
assert t_admin.status_code == 200 and t_viewer.status_code == 200

admin_token = t_admin.json()["access_token"]
viewer_token = t_viewer.json()["access_token"]
h_admin = {"Authorization": f"Bearer {admin_token}"}
h_viewer = {"Authorization": f"Bearer {viewer_token}"}

k_admin = c.post("/generate-key/", headers=h_admin)
k_viewer = c.post("/generate-key/", headers=h_viewer)
assert k_admin.status_code == 200 and k_viewer.status_code == 200

hk_admin = {"Authorization": f"Bearer {admin_token}", "X-API-Key": k_admin.json()["api_key"]}
hk_viewer = {"Authorization": f"Bearer {viewer_token}", "X-API-Key": k_viewer.json()["api_key"]}

# Ensure roles for deterministic smoke run.
db = Session(bind=engine)
try:
    for name in ("Admin", "Editor", "Viewer"):
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name))
    db.commit()

    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    viewer_role = db.query(Role).filter(Role.name == "Viewer").first()
    assert admin_role and viewer_role
    db.query(UserRole).filter(UserRole.user_id.in_([r1.json()["id"], r2.json()["id"]])).delete(
        synchronize_session=False
    )
    db.add(UserRole(user_id=r1.json()["id"], role_id=admin_role.id))
    db.add(UserRole(user_id=r2.json()["id"], role_id=viewer_role.id))
    db.commit()
finally:
    db.close()

perm_admin = c.get("/users/permissions/", headers=hk_admin)
perm_viewer = c.get("/users/permissions/", headers=hk_viewer)
assert perm_admin.status_code == 200 and perm_viewer.status_code == 200

assign = c.post("/roles/assign/", headers=hk_admin, json={"user_id": r2.json()["id"], "role": "Editor"})
assert assign.status_code == 200, assign.text
forbidden_assign = c.post("/roles/assign/", headers=hk_viewer, json={"user_id": r1.json()["id"], "role": "Viewer"})
assert forbidden_assign.status_code == 403

# Generate usage data and verify admin analytics access.
assert c.get("/posts/mine", headers=hk_viewer).status_code == 200
summary = c.get("/analytics/summary/", headers=hk_admin)
top_users = c.get("/analytics/top-users/", headers=hk_admin)
plan_dist = c.get("/analytics/plan-distribution/", headers=hk_admin)
assert summary.status_code == 200 and top_users.status_code == 200 and plan_dist.status_code == 200
assert c.get("/analytics/summary/", headers=hk_viewer).status_code == 403

# Admin-only user delete.
delete_try = c.delete(f"/users/{r1.json()['id']}/", headers=hk_viewer)
assert delete_try.status_code == 403

# Chat REST + websocket checks.
chat_hist = c.get("/chat/history", headers=hk_admin)
assert chat_hist.status_code == 200
pm = c.post("/chat/private", headers=hk_admin, json={"receiver_id": r2.json()["id"], "message": "hello private"})
assert pm.status_code == 200, pm.text

with c.websocket_connect(f"/chat/?token={admin_token}") as ws_admin:
    with c.websocket_connect(f"/chat/?token={viewer_token}") as ws_viewer:
        ws_admin.send_text("hello all")
        msg1 = ws_admin.receive_json()
        msg2 = ws_viewer.receive_json()
        assert msg1["type"] == "chat_message" and msg2["type"] == "chat_message"

print("task11 fullstack ok")
