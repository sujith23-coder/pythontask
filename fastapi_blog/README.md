# Task 6 — Blog Management API (FastAPI)

New FastAPI project (separate from Django). **SQLite** + **SQLAlchemy**, **JWT** auth for writes, **public reads** for posts and comments.

## Run

```bash
cd fastapi_blog
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Swagger:** http://127.0.0.1:8000/docs  
- **DB file:** `blog.db` (created automatically)

## Auth

1. `POST /auth/register` — JSON: `username`, `email`, `password`
2. `POST /auth/login` — form (`application/x-www-form-urlencoded`): `username`, `password` → use **Authorize** in Swagger or `Authorization: Bearer <token>`

## Endpoints (summary)

| Method | Path | Auth |
|--------|------|------|
| POST | `/auth/register` | No |
| POST | `/auth/login` | No |
| POST | `/posts/` | JWT |
| GET | `/posts/` | No |
| GET | `/posts/mine` | JWT (optional) |
| GET | `/posts/{id}` | No |
| PUT | `/posts/{id}` | JWT (owner) |
| DELETE | `/posts/{id}` | JWT (owner) |
| POST | `/posts/{id}/comments/` | JWT |
| GET | `/posts/{id}/comments/` | No |
| POST | `/posts/{id}/like/` | JWT (toggle) |
| GET | `/posts/{id}/likes/` | No |
| POST | `/email/send-notification/` | JWT (manual queue) |

## Email notifications

On **new comment** or **new like** (not unlike), the **post owner** receives an email via `BackgroundTasks`.

- **Without SMTP:** messages are printed to the server console (demo).
- **With SMTP**, set env vars: `SMTP_HOST`, `SMTP_PORT` (default `587`), `SMTP_USER`, `SMTP_PASSWORD`, `FROM_EMAIL`.

## Testing

```bash
python scripts/smoke_test.py
```

Import `task6_postman.json` into Postman.

## Submission screenshots

- SQLite tables: `users`, `posts`, `comments`, `likes`
- Postman: register, login, CRUD post, comments, likes, 403/404 errors, email endpoint
- Swagger `/docs`
