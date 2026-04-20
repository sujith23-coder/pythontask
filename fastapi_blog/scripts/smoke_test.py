import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

if os.path.exists("blog.db"):
    os.remove("blog.db")
Base.metadata.create_all(bind=engine)

c = TestClient(app)
r = c.post(
    "/auth/register",
    json={"username": "author", "email": "a@t.com", "password": "password123"},
)
assert r.status_code == 201, r.text
r2 = c.post(
    "/auth/register",
    json={"username": "reader", "email": "r@t.com", "password": "password123"},
)
assert r2.status_code == 201
t = c.post("/auth/login", data={"username": "author", "password": "password123"})
tok = t.json()["access_token"]
h = {"Authorization": f"Bearer {tok}"}
p = c.post("/posts/", headers=h, json={"title": "Hi", "content": "Body"})
assert p.status_code == 201, p.text
pid = p.json()["id"]
assert c.get(f"/posts/{pid}").status_code == 200
t2 = c.post("/auth/login", data={"username": "reader", "password": "password123"})
tok2 = t2.json()["access_token"]
h2 = {"Authorization": f"Bearer {tok2}"}
cm = c.post(f"/posts/{pid}/comments/", headers=h2, json={"text": "Nice"})
assert cm.status_code == 201, cm.text
lk = c.post(f"/posts/{pid}/like/", headers=h2)
assert lk.status_code == 200 and lk.json()["liked"] is True
lk2 = c.post(f"/posts/{pid}/like/", headers=h2)
assert lk2.json()["liked"] is False
m = c.get("/posts/mine", headers=h)
assert len(m.json()) == 1
bad = c.put(f"/posts/{pid}", headers=h2, json={"title": "x"})
assert bad.status_code == 403
print("all ok")
