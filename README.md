# Django Signup Login Logout Task

This project implements:

- User signup API
- User login API
- User logout API
- User profile fetch and update APIs
- Password change API
- Profile picture upload API

## Tech Stack

- Django
- MySQL
- PyMySQL
- Pillow

## Project Structure

- `auth_project/` - Django project settings and root URLs
- `accounts/` - Authentication and profile app
- `requirement.txt` - Python package list
- `.env.sample` - Sample database configuration values

## Setup

1. Create and activate virtual environment (optional but recommended).
2. Install dependencies:

```bash
pip install -r requirement.txt
```

3. Copy `.env.sample` values into your environment variables:

- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_HOST`
- `MYSQL_PORT`

4. Ensure MySQL server is running and database exists.
5. Run migrations:

```bash
python manage.py migrate
```

6. Start the server:

```bash
python manage.py runserver
```

## API Endpoints

### 1) Signup

- **URL:** `POST /signup/`
- **Body (JSON):**

```json
{
  "username": "john",
  "password": "12345",
  "email": "john@example.com"
}
```

### 2) Login

- **URL:** `POST /login/`
- **Body (JSON):**

```json
{
  "username": "john",
  "password": "12345"
}
```

### 3) Logout

- **URL:** `POST /logout/`

### 4) Get Profile

- **URL:** `GET /profile/`
- Requires logged-in session.

### 5) Update Profile

- **URL:** `POST /profile/update/`
- **Body (JSON) example:**

```json
{
  "username": "john_new",
  "email": "john_new@example.com",
  "additional_details": "Profile details"
}
```

### 6) Change Password

- **URL:** `POST /change-password/`
- **Body (JSON):**

```json
{
  "old_password": "12345",
  "new_password": "54321"
}
```

### 7) Upload Profile Photo

- **URL:** `POST /profile/photo/`
- **Body:** form-data with key `profile_picture` as file

## Notes

- Profile model is linked one-to-one with Django `User`.
- Uploaded profile images are stored under `media/profile_pictures/`.
- APIs are intended to be tested with Postman.
