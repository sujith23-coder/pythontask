# Parking Management System (Task 4)

Separate Django project from the blog app. Uses **SQLite3**, **Bootstrap 4.6**, and **Django REST Framework** for APIs.

## Features

- **Administrator** model linked to Django `User` (staff-only web login).
- **Category**: parking area number, vehicle type, limit, charge, activated/deactivated status.
- **Vehicle**: receipt serial (`PMS-######`), vehicle number, area, type, hourly charge snapshot, parked/leaved, arrival/departure, computed fee on exit.
- **Web UI**: Dashboard (6 KPI cards), category CRUD + activate/deactivate, vehicle entry with capacity sidebar, manage vehicles (30-day window, **Done** = exit), 10-day report, search by plate or receipt (30 days), account password + optional departure email toggle.
- **Auth**: Login, logout, Django password reset (email prints to console in dev).
- **API**: `/api/categories/`, `/api/vehicles/`, `POST /api/vehicles/<id>/depart/`. Optional filter `?q=` for search.

## Setup

```bash
cd parking_system
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

Enable **Staff status** for the user in admin (or tick “Staff” when creating). Only staff can sign in to the PMS.

```bash
python manage.py runserver
```

- Web: http://127.0.0.1:8000/ (redirects to login if needed)
- Admin: http://127.0.0.1:8000/admin/
- Swagger: not included; use Postman collection `task4_postman.json` with **Basic Auth**.

## Postman

Import `task4_postman.json`. Set collection variables `username`, `password`, and use **Authorization → Basic Auth** (or enable it in each request).

## Submission screenshots (suggested)

- SQLite DB (DB Browser or IDE): `administrator`, `category`, `vehicle` tables.
- Frontend: login, dashboard, category, vehicle entry, manage, reports, search, account, printed receipt.
- Postman: CRUD + depart + errors.
- Console: password reset email + optional departure notification.

## Assignment PDF alignment

UI layout and flows follow the RamanaSoft mockups (sidebar, KPI cards, category table, limitations panel, **Done** for departure, 10-day report, search, change password). Stack per your brief: Django + Bootstrap + **SQLite** (PDF may mention MySQL; this project uses SQLite as required).
