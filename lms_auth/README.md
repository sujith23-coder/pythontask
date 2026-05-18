# LMS Authentication System

Social login (Google, Facebook, GitHub), OTP-based login/signup, JWT tokens, and a Django admin panel for users, social accounts, and OTP logs.

## Tech stack

- **FastAPI** — OAuth2 and OTP API routes
- **Django** — `User`, `SocialAccount`, `OTPLog` models and admin
- **JWT** — issued after successful OAuth or OTP verification
- **SQLite** — default database (shared by FastAPI via Django ORM)

## Project structure

```
lms_auth/
  app/
    main.py
    auth_utils.py          # JWT helpers
    routers/
      auth_google.py
      auth_facebook.py
      auth_github.py
      auth_otp.py
  django_lms/
    manage.py
    lms_project/
    accounts/
      models.py            # SocialAccount, OTPLog
      admin.py
  requirements.txt
  lms_auth_postman.json
  .env.sample
```

## Setup

### 1. Install dependencies

```bash
cd lms_auth
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Environment variables

Copy the sample file and fill in OAuth credentials:

```bash
copy .env.sample .env
```

| Variable | Description |
|----------|-------------|
| `JWT_SECRET_KEY` | Secret for signing JWTs |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google Cloud OAuth client |
| `GOOGLE_REDIRECT_URI` | Must match Google console (default `http://127.0.0.1:8000/auth/google/callback`) |
| `FACEBOOK_CLIENT_ID` / `FACEBOOK_CLIENT_SECRET` | Meta developer app |
| `FACEBOOK_REDIRECT_URI` | Facebook app OAuth redirect |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth app |
| `GITHUB_REDIRECT_URI` | GitHub app callback URL |
| `SMTP_*` | Optional; without SMTP, OTP codes print in the API console |

### 3. Database migrations

```bash
cd django_lms
python manage.py migrate
python manage.py createsuperuser
cd ..
```

### 4. Run services

**FastAPI (port 8000):**

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Django admin (port 8001):**

```bash
cd django_lms
python manage.py runserver 8001
```

Open `http://127.0.0.1:8001/admin/` to manage users, social accounts, and OTP logs.

API docs: `http://127.0.0.1:8000/docs`

## OAuth provider setup

### Google

1. Open [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Create an **OAuth 2.0 Client ID** (Web application).
3. Add authorized redirect URI: `http://127.0.0.1:8000/auth/google/callback`
4. Copy Client ID and Client Secret into `.env`.

### Facebook

1. Create an app at [Meta for Developers](https://developers.facebook.com/apps/).
2. Add **Facebook Login** product.
3. Set Valid OAuth Redirect URI: `http://127.0.0.1:8000/auth/facebook/callback`
4. Copy App ID and App Secret to `FACEBOOK_CLIENT_ID` and `FACEBOOK_CLIENT_SECRET`.

### GitHub

1. Go to [GitHub Developer Settings](https://github.com/settings/developers) → **OAuth Apps** → **New OAuth App**.
2. Authorization callback URL: `http://127.0.0.1:8000/auth/github/callback`
3. Copy Client ID and generate a Client Secret for `.env`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/auth/google/login` | Returns Google authorization URL + state |
| GET/POST | `/auth/google/callback` | Exchange code for JWT |
| GET | `/auth/facebook/login` | Facebook authorization URL |
| GET/POST | `/auth/facebook/callback` | Exchange code for JWT |
| GET | `/auth/github/login` | GitHub authorization URL |
| GET/POST | `/auth/github/callback` | Exchange code for JWT |
| POST | `/auth/otp/request` | Send OTP to email/phone |
| POST | `/auth/otp/verify` | Verify OTP and receive JWT |
| GET | `/auth/otp/me` | Current user (Bearer JWT) |

### OAuth flow

1. Call `GET /auth/{provider}/login` and open `authorization_url` in a browser.
2. After consent, the provider redirects to `/auth/{provider}/callback?code=...&state=...`
3. Response includes `access_token` (JWT), `user_id`, `username`, and `is_new_user`.

For mobile/SPA clients, use `POST /auth/{provider}/callback` with JSON `{"code": "...", "state": "..."}`.

### OTP flow

**Signup**

```json
POST /auth/otp/request
{ "identifier": "user@example.com", "purpose": "signup" }

POST /auth/otp/verify
{ "identifier": "user@example.com", "otp": "123456", "purpose": "signup", "username": "optional_name" }
```

**Login**

```json
POST /auth/otp/request
{ "identifier": "user@example.com", "purpose": "login" }

POST /auth/otp/verify
{ "identifier": "user@example.com", "otp": "123456", "purpose": "login" }
```

Without SMTP configured, the OTP appears in the terminal running uvicorn as `[OTP] user@example.com: 123456`.

### Authenticated requests

```http
Authorization: Bearer <access_token>
GET /auth/otp/me
```

## Postman

Import `lms_auth_postman.json`. Set collection variables:

- `base_url` — `http://127.0.0.1:8000`
- `token` — filled after OTP verify or OAuth callback

## Django admin

Registered models:

- **Users** — Django auth users
- **Social accounts** — linked Google/Facebook/GitHub identities
- **OTP logs** — identifier, purpose, verification status, attempts, expiry
- **Courses, Enrollments, Attendance, Assignments, Submissions, Notifications**

---

## Advanced LMS Features (Task 5)

### Sample data

```bash
cd django_lms
python manage.py migrate
python manage.py load_sample_data
cd ..
python scripts/issue_token.py faculty1    # faculty JWT
python scripts/issue_token.py student1    # student JWT
```

| User | Password (Django admin) | Role |
|------|-------------------------|------|
| `faculty1` | `faculty123` | Course instructor |
| `student1`–`student3` | `student123` | Enrolled students |

Use `scripts/issue_token.py` for API JWTs during local testing.

### Attendance (FastAPI)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/attendance/mark` | Instructor JWT | Bulk mark attendance |
| GET | `/attendance/student/{id}?course_id=` | Student or instructor | Student attendance + % |
| GET | `/attendance/course/{id}?from=&to=` | Instructor JWT | Course attendance log |

**Rules:** No duplicate student/course/date; students must be enrolled; only course instructor can mark.

```json
POST /attendance/mark
{
  "course_id": 1,
  "date": "2025-10-30",
  "records": [
    {"student_id": 2, "status": "Present"},
    {"student_id": 3, "status": "Absent"}
  ]
}
```

### Assignments (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/assignments/create` | Multipart: `title`, `description`, `deadline`, `course_id`, optional `file` |
| POST | `/assignments/submit` | Multipart: `assignment_id`, `student_id`, `file` |
| PUT | `/assignments/grade` | JSON: `submission_id`, `grade`, `remarks` |
| GET | `/assignments/course/{course_id}` | List assignments |

**Rules:** Faculty only create/grade; no submission after deadline; file versioning on resubmit.

### Analytics (Django — port 8001)

| Method | Path |
|--------|------|
| GET | `http://127.0.0.1:8001/analytics/dashboard/?course_id=1` |
| GET | `http://127.0.0.1:8001/analytics/course-summary/?course_id=1` |

Response example:

```json
{
  "course_id": 1,
  "total_students": 3,
  "avg_attendance": 85.5,
  "total_assignments": 1,
  "submissions_count": 0,
  "graded_submissions": 0
}
```

### Notifications (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/notifications/{user_id}` | List notifications (`?unread_only=true`) |
| POST | `/notifications/mark-read` | `{ "notification_ids": [1,2] }` or `{ "mark_all": true }` |

Triggered automatically when: assignment created, submission graded, attendance marked.

### Postman

- `lms_auth_postman.json` — authentication
- `lms_advanced_postman.json` — attendance, assignments, notifications, analytics

### Tests

```bash
cd django_lms
pytest ../tests -v
```
