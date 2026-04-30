# Blog + Subscription API (Tasks 6–7)

Combined **FastAPI** app:

1. **Blog (SQLAlchemy)** — posts, comments, likes, JWT, `BackgroundTasks` email (Task 6).
2. **Subscription & billing (Django ORM)** — plans, billing history, ReportLab PDF invoices (Task 7).
3. **API key + usage tracking (Django ORM + FastAPI middleware)** — per-user API keys, per-endpoint counters, daily limits (Task 8).
4. **Admin analytics dashboard (FastAPI + HTML)** — summary metrics, daily usage analytics, lightweight frontend (Task 10).
5. **Full-stack integration (Task 11)** — RBAC, real-time chat (WebSocket), admin analytics protection.

Both use the **same SQLite file**: `blog.db` at the project root.

## Setup

```bash
cd fastapi_blog
pip install -r requirements.txt
```

### 1) Create SQLAlchemy tables + run Django migrations

On first setup (or when `blog.db` is new):

```bash
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
cd django_billing
python manage.py migrate
cd ..
```

Starting **uvicorn** also runs `create_all` + `django.setup()`; migrations should be applied at least once so `subscription_*` tables exist.

### 2) Run API

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Swagger:** http://127.0.0.1:8000/docs  
- **Invoices (PDFs):** `invoices/` folder (created automatically)

## Blog API (Task 6)

| Method | Path | Auth |
|--------|------|------|
| POST | `/auth/register` | No |
| POST | `/auth/login` | No (form) |
| POST | `/posts/` | JWT |
| GET | `/posts/`, `/posts/{id}` | No |
| GET | `/posts/mine` | JWT |
| PUT / DELETE | `/posts/{id}` | JWT (owner) |
| POST | `/posts/{id}/comments/` | JWT |
| GET | `/posts/{id}/comments/` | No |
| POST | `/posts/{id}/like/` | JWT |
| GET | `/posts/{id}/likes/` | No |
| POST | `/email/send-notification/` | JWT |

## Subscription & billing (Task 7)

Django models live in `django_billing/subscription/models.py`:

- **SubscriptionPlan** — `name`, `price` (INR), `duration` (days)
- **BillingHistory** — `user` → `users` table (unmanaged `BlogUser`), `plan`, `start_date`, `end_date`, `invoice` (absolute PDF path), `transaction_id`

| Method | Path | Auth |
|--------|------|------|
| POST | `/subscribe/` | JWT — body `{"plan_id": 1}` |
| GET | `/subscription/me` | JWT — active row (`end_date >= now`) |
| GET | `/billing/history` | JWT — all billing rows for user |

**Subscribe** creates a `BillingHistory` row, sets `end_date = start_date + plan.duration`, generates a **ReportLab** PDF (user name, plan, INR price, dates, transaction id), saves path on the row, and queues a **confirmation email** (console or SMTP).

**Seed plans:** migration `0002_seed_plans` — Basic (299 / 30d), Pro (799 / 30d), Premium (1499 / 90d).

## API key & usage tracking (Task 8)

Django models in `django_billing/subscription/models.py`:

- **APIKey** — `user`, unique `key`, `created_at`
- **APIUsage** — `user`, `endpoint`, `total_requests`, `last_used`, `usage_date`

| Method | Path | Auth |
|--------|------|------|
| POST | `/generate-key/` | JWT |
| GET | `/usage/` | JWT |

Middleware behavior:

- For JWT-authenticated requests (except `/auth/*`, `/generate-key/`, `/usage/`, docs endpoints), `X-API-Key` is required.
- API key must belong to the same authenticated user.
- Requests are auto-counted in `APIUsage`.
- Daily rate limits by active plan: `Basic=100`, `Pro=500`, fallback/default=`100`. Exceeded limit returns **HTTP 429**.

## Admin analytics dashboard (Task 10)

Endpoints:

| Method | Path | Auth |
|--------|------|------|
| GET | `/admin/analytics/summary` | JWT + `X-API-Key` |
| GET | `/admin/analytics/usage-daily` | JWT + `X-API-Key` |
| GET | `/admin/analytics/dashboard` | No auth (HTML page; API calls still require JWT + key) |

`/admin/analytics/summary` returns:

- `total_users`
- `total_requests`
- `top_users` (top 5 by API requests)
- `plan_distribution` (active plan counts)

`/admin/analytics/usage-daily` returns daily request totals for the last 7 days.

Frontend dashboard:

- Cards for totals and plan split
- Top users list
- Bar chart (Chart.js CDN) for last 7 days usage
- Input fields for Bearer token and API key to load data

## Full Stack System (Task 11)

### RBAC

Roles auto-seeded at startup: `Admin`, `Editor`, `Viewer`.

- `POST /roles/assign/` — Admin only
- `GET /users/permissions/` — current user role + permissions
- `DELETE /users/{id}/` — Admin only

Bootstrap behavior:
- First registered user gets `Admin`
- Later users default to `Viewer`

### Real-time chat

- WebSocket endpoint: `ws://127.0.0.1:8000/chat/?token=<JWT>`
- Public broadcast messages: send plain text
- Optional private WS message format: `@<user_id> <message>`
- REST helpers:
  - `GET /chat/history`
  - `POST /chat/private`
  - `GET /chat/private/history/{other_user_id}`

Chat message persistence:
- `chat_messages` table (public chat history)
- `private_messages` table (1:1 history)

### Analytics security integration

- `/admin/analytics/*` and `/analytics/*` endpoints now require Admin role.
- Existing API-key middleware still applies to authenticated HTTP requests.

## Email

Blog comments/likes and subscription confirmation use `BackgroundTasks` + `app/services/email.py`.

- No SMTP: logs to **console**.
- Optional: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `FROM_EMAIL`.

## Tests / Postman

```bash
python scripts/smoke_test.py
python scripts/task7_billing_smoke.py
python scripts/task10_analytics_smoke.py
python scripts/task11_fullstack_smoke.py
```

- `task6_postman.json` — blog flows  
- `task7_postman.json` — subscribe / subscription / billing  
- `task8_postman.json` — API key generation / usage tracking / rate limit checks
- `task10_postman.json` — admin analytics endpoints + dashboard page
- `task11_postman.json` — RBAC + chat + secured analytics flows

## Submission (screenshots)

- SQLite: `users`, `posts`, `comments`, `likes`, `subscription_subscriptionplan`, `subscription_billinghistory`, `django_content_type`
- Swagger + Postman for blog and billing
- Sample **PDF** under `invoices/`
- Django: show models in IDE or DB browser + seeded plans

## Security

Change JWT `SECRET_KEY` in `app/auth.py` and Django `SECRET_KEY` in `django_billing/billing_project/settings.py` for production.
