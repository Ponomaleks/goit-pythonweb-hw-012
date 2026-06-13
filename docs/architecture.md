# Architecture

## Goal

Provide an async REST API for contacts management with authentication, user ownership, email verification, avatar support, and predictable error handling.

## Stack

- FastAPI for HTTP routing and OpenAPI docs
- SQLAlchemy 2.x async ORM/session
- PostgreSQL
- Alembic migrations
- Pydantic v2 schemas
- JWT access tokens via `python-jose`
- FastAPI-Mail for verification emails
- SlowAPI for request limiting
- Cloudinary for avatar uploads

## Implemented Layering

1. API layer
   - Routers in `app/api/v1/endpoints/auth.py`, `contacts.py`, and `users.py`
   - Pydantic request/response validation
   - Authentication and ownership enforced via dependencies
2. Dependency layer
   - `app/api/dependencies.py` resolves the current user from Bearer tokens
   - `app/db/dependencies.py` provides request-scoped DB sessions
   - `app/core/limiter.py` provides rate limiting
3. Service layer
   - Business rules in `app/services/auth.py`, `contact.py`, `avatar.py`, and `mailer.py`
   - Password hashing, JWT creation/validation, email verification, and avatar upload orchestration
4. Repository layer
   - Data access in `app/repositories/user.py` and `contact.py`
   - Query composition and persistence operations
   - `flush()` without `commit()` for transactional control
5. ORM layer
   - SQLAlchemy models in `app/models/user.py` and `contact.py`
   - Contacts are scoped by `user_id`
   - User records store `is_verified` and `avatar_url`
6. Infrastructure layer
   - Settings in `app/config/config.py`
   - DB engine/session in `app/db/session.py`
   - Alembic configuration in `migrations/env.py`
   - CORS and exception handlers in `app/main.py`

## Package Structure

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

## API Surface

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

## Data and Validation Rules

- Passwords are hashed before persistence.
- Access tokens are JWTs with an expiration time and are not stored in the database.
- Contacts belong to a single user via `user_id`.
- Contact email uniqueness is enforced per user.
- Login is allowed only after the user's email is verified.
- Search supports first name, last name, and email with OR matching.
- `GET /api/v1/users/me` is rate-limited.
- Default avatars are generated from Gravatar; uploaded avatars replace `avatar_url` via Cloudinary.
- `CORS_ALLOWED_ORIGINS` may be provided as either a JSON array string or a comma-separated list.

## Error Handling Model

- Repository returns ORM objects and lets DB exceptions bubble up.
- Service converts business-rule failures into domain or HTTP exceptions.
- FastAPI app-level handlers map errors to HTTP responses:
  - `ContactNotFoundError -> 404`
  - `ContactAlreadyExistsError -> 409`
  - `UserAlreadyExistsError -> 409`
  - `InvalidCredentialsError -> 401`
  - `UserNotFoundError -> 404`
  - `ApplicationError -> 400`

## Scope Notes

- Authentication and authorization are implemented and required for user-scoped operations.
- Automated tests are not part of the current delivery scope.
