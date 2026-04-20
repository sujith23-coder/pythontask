# Django User, Blog, Gallery, Comment, and Activity APIs

This project contains all tasks implemented in the same `accounts` app: user/profile management, blog posts, image gallery, comments with search, activity feed, notification preferences, and Swagger docs.

## Tech Stack

- Django
- Django REST Framework
- drf-yasg (Swagger / ReDoc)
- MySQL
- PyMySQL
- Pillow

## Project Structure

- `auth_project/` - project settings and root URL config
- `accounts/` - auth, profile, blog, gallery, comment, activity, notifications
- `accounts/models.py` - `Profile`, `UserData`, `Post`, `Image`, `Comment`, `Activity`
- `accounts/views.py` - all API view functions
- `accounts/urls.py` - all API routes
- `task1_postman.json` - auth/profile API collection
- `task2_postman.json` - blog/gallery API collection
- `task3_postman.json` - comment/activity/notification + error cases

## Setup

1. Install dependencies:

```bash
pip install -r requirement.txt
```

2. Configure database environment variables:

- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_HOST`
- `MYSQL_PORT`

3. Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

4. Run server:

```bash
python manage.py runserver
```

## Existing User/Profile APIs

- Signup: `POST /signup/`
- Login: `POST /login/`
- Logout: `POST /logout/`
- Profile: `GET /profile/`
- Update Profile: `POST /profile/update/`
- Change Password: `POST /change-password/`
- Upload Profile Photo: `POST /profile/photo/`

## Blog Post Module

### Model

`Post` fields:
- `title`
- `content`
- `author`
- `created_at`
- `updated_at`

### APIs

- Create Post: `POST /posts/create/`
- List Posts: `GET /posts/`
- View Post: `GET /posts/<id>/`
- Update Post: `POST /posts/<id>/update/` (author only)
- Delete Post: `POST /posts/<id>/delete/` (author only)

## Image Gallery Module

### Model

`Image` fields:
- `title`
- `image`
- `uploaded_by`
- `post` (nullable)
- `uploaded_at`

### APIs

- Upload Image: `POST /gallery/upload/`
- List Images: `GET /gallery/?page=<n>` (10 per page)
- View Image: `GET /gallery/<id>/`
- Update Image: `POST /gallery/<id>/update/` (uploader only)
- Delete Image: `POST /gallery/<id>/delete/` (uploader only)

## Comment System (Task 3)

### Model

`Comment` fields:
- `content`
- `author`
- `post`
- `created_at`
- `updated_at`

### APIs

- Create Comment: `POST /comments/create/` (authenticated user)
- List Comments: `GET /comments/?page=<n>&page_size=<n>&post=<post_id>`
- Search Comments: `GET /comments/search/?q=<keyword>&page=<n>&page_size=<n>`
- Update Comment: `POST /comments/<id>/update/` (author only)
- Delete Comment: `POST /comments/<id>/delete/` (author only)

## Email Notifications & Activity Feed (Task 3)

### Models

`Activity` fields:
- `user`
- `action_type` (`comment`, `like`)
- `target_id`
- `target_type` (`post`, `comment`)
- `created_at`

`UserData` fields:
- `user`
- `email_notifications_enabled`

### APIs

- Create Activity: `POST /activities/create/`
- List User Activities: `GET /activities/?page=<n>&page_size=<n>`
- Toggle Notifications: `POST /notifications/toggle/`

### Email behavior

- Comment creation sends an email to the post owner (if notifications are enabled).
- Like activity sends an email to the target owner (if notifications are enabled).
- Email output is logged via Django console email backend.

## API Documentation

- Swagger UI: `GET /api/docs/`
- ReDoc: `GET /api/redoc/`

## Testing Checklist

- Test all APIs via Postman collections (`task1_postman.json`, `task2_postman.json`, `task3_postman.json`)
- Include successful and error cases:
  - Unauthorized access
  - Author-only update/delete failures
  - Invalid payloads
  - Missing/invalid target references

## Submission Checklist

- DB table screenshots: `Post`, `Image`, `Comment`, `Activity`, `UserData`
- Postman request/response screenshots
- Swagger screenshot (`/api/docs/`)
- Email console log screenshots for notifications
- Frontend screenshots (if implemented)
- Submit complete project folder **without ZIP format**

## Notes

- All features are implemented in existing `accounts` app.
- No new Django app is created.
- Uploaded media files are stored under `media/`.
