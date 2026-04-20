# Blog + Subscription API (Tasks 6–7)

Combined **FastAPI** app:

1. **Blog (SQLAlchemy)** — posts, comments, likes, JWT, `BackgroundTasks` email (Task 6).
2. **Subscription & billing (Django ORM)** — plans, billing history, ReportLab PDF invoices (Task 7).

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

## Email

Blog comments/likes and subscription confirmation use `BackgroundTasks` + `app/services/email.py`.

- No SMTP: logs to **console**.
- Optional: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `FROM_EMAIL`.

## Tests / Postman

```bash
python scripts/smoke_test.py
python scripts/task7_billing_smoke.py
```

- `task6_postman.json` — blog flows  
- `task7_postman.json` — subscribe / subscription / billing  

## Submission (screenshots)

- SQLite: `users`, `posts`, `comments`, `likes`, `subscription_subscriptionplan`, `subscription_billinghistory`, `django_content_type`
- Swagger + Postman for blog and billing
- Sample **PDF** under `invoices/`
- Django: show models in IDE or DB browser + seeded plans

## Security

Change JWT `SECRET_KEY` in `app/auth.py` and Django `SECRET_KEY` in `django_billing/billing_project/settings.py` for production.
