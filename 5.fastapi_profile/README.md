# Task 5 — User Profile Management API (FastAPI)

Separate project from Django work. **SQLite** + **SQLAlchemy** + **JWT** (`python-jose`) + **bcrypt** (password hashing).

## Features

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/register` | POST | No | Create account (username, email, password, bio). Returns profile JSON (no password). |
| `/auth/token` | POST | No | OAuth2 password form → JWT (`access_token`). Use **username** + **password**. |
| `/profiles/` | POST | JWT | Create another profile (requires existing token). |
| `/profiles/me` | GET | JWT | Optional: current user’s profile. |
| `/profiles/{id}` | GET | JWT | Read profile by id. |
| `/profiles/{id}` | PUT | JWT | Update (owner only). |
| `/profiles/{id}` | DELETE | JWT | Delete (owner only). |

- **Validation**: Pydantic (`EmailStr`, min length username, unique checks → `400` with `Email already registered` etc.).
- **Errors**: `401` invalid/missing JWT, `403` wrong owner on PUT/DELETE, `404` missing profile.
- **Swagger**: http://127.0.0.1:8000/docs  
- **ReDoc**: http://127.0.0.1:8000/redoc  
- **Rate limiting**: `slowapi` middleware (per-route limits).

## Run

```bash
cd fastapi_profile
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Database file: `profiles.db` in the `fastapi_profile` folder (created on first start).

## Typical flow (Postman)

1. **POST** `/auth/register` — JSON body with `username`, `email`, `password`, `bio`.
2. **POST** `/auth/token` — `x-www-form-urlencoded`: `username`, `password` → copy `access_token`.
3. **Authorization**: Bearer token for `/profiles/*`.
4. **POST** `/profiles/` — create second user while authenticated as first (demo).

Import `task5_postman.json` for ready-made requests.

## Security note

Change `SECRET_KEY` in `app/auth.py` (or env) before production.

## Submission screenshots

- SQLite `user_profiles` table with sample rows.
- Postman: register, token, CRUD, duplicate email, wrong owner (403), missing id (404).
- Swagger `/docs` showing operations and **Authorize** with Bearer token.
