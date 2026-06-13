# Contacts API

Async REST API for contact management built with FastAPI, SQLAlchemy 2.x, PostgreSQL, Alembic, Pydantic v2, JWT auth, FastAPI-Mail, SlowAPI, and Cloudinary.

## What is implemented

- JWT-based authentication with signup, login, and current-user profile access.
- Email verification flow with verification and resend endpoints.
- User-scoped contacts: each contact belongs to exactly one user.
- Search, upcoming birthdays, full update, partial update, and delete for contacts.
- Rate limiting on `GET /api/v1/users/me`.
- Default avatar generation with Gravatar and manual avatar replacement via Cloudinary.
- CORS configuration from environment variables.
- Docker Compose setup with automatic Alembic migration on API startup.

## API Endpoints

- `POST /api/v1/auth/signup`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/verify`
- `POST /api/v1/auth/resend-verification`
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me/avatar`
- `POST /api/v1/contacts`
- `GET /api/v1/contacts`
- `GET /api/v1/contacts/search`
- `GET /api/v1/contacts/{contact_id}`
- `PUT /api/v1/contacts/{contact_id}`
- `PATCH /api/v1/contacts/{contact_id}`
- `DELETE /api/v1/contacts/{contact_id}`
- `GET /api/v1/contacts/birthdays/upcoming`
- `GET /health`

## Project Structure

```text
app/
  main.py
  api/
    dependencies.py
    v1/
      endpoints/
        auth.py
        contacts.py
        users.py
  config/
    config.py
  core/
    limiter.py
  db/
    base.py
    session.py
    dependencies.py
  models/
    contact.py
    user.py
  repositories/
    contact.py
    user.py
  schemas/
    contact.py
    user.py
  services/
    auth.py
    avatar.py
    contact.py
    mailer.py
  exceptions.py
migrations/
docs/
```

## Setup

```bash
cp .env.example .env
```

Copy `.env.example` to `.env`, then fill in the values for your environment.

## Run

Docker Compose:

```bash
docker compose up --build
```

Local development:

## API Docs

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Notes

- Login uses `OAuth2PasswordRequestForm`, so Swagger UI sends `application/x-www-form-urlencoded` with `username` and `password` fields.
- Login requires a verified email address.
- POST create endpoints return `201 Created`.
- Access tokens are JWTs with an expiration time and are not stored in the database.
- Environment secrets live in `.env`, which is created from `.env.example`.
- `CORS_ALLOWED_ORIGINS` accepts either a JSON-style list or a comma-separated string.
