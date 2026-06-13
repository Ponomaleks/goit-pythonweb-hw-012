# Project Context

This is a production-style REST API built with FastAPI.

The application follows a layered architecture with clear separation of concerns and async-first design.

---

## Tech Stack

- FastAPI (async REST API)
- SQLAlchemy 2.x (async ORM)
- PostgreSQL
- Alembic (database migrations)
- Pydantic v2 (validation layer)
- JWT authentication (python-jose)
- Redis (caching + token storage)
- FastAPI-Mail (email delivery)
- SlowAPI (rate limiting)
- Cloudinary (file storage)
- Pytest + pytest-cov (testing)
- Sphinx (documentation)
- Docker + Docker Compose (containerized environment)

---

## Current Architecture (DO NOT BREAK)

The project is strictly layered:

### API Layer

- app/api/v1/endpoints/\*
- Responsible ONLY for HTTP handling
- Must NOT contain business logic

### Dependency Layer

- app/api/dependencies.py
- app/db/dependencies.py
- Authentication, DB session, rate limiting, user resolution

### Service Layer

- app/services/\*
- Contains all business logic
- Must be framework-aware but not HTTP-dependent

### Repository Layer

- app/repositories/\*
- Handles DB queries only
- No business logic allowed

### ORM Layer

- app/models/\*
- SQLAlchemy models only

### Infrastructure Layer

- app/config/config.py
- app/db/session.py
- app/main.py
- migrations/

---

## Existing API Surface (DO NOT REMOVE OR BREAK)

Auth:

- POST /auth/signup
- POST /auth/login
- GET /auth/verify
- POST /auth/resend-verification

Users:

- GET /users/me
- PATCH /users/me/avatar

Contacts:

- CRUD + search + birthdays endpoints

System:

- GET /health

---

## Critical Design Rules

### Architecture Rules

- Never put business logic in routers
- Always use service layer for logic
- Repository layer must only handle DB operations
- Keep functions small and single responsibility

### Async Rules

- All DB operations must be async
- Never block event loop with sync IO

### Security Rules

- Never expose secrets or tokens in responses
- All secrets must come from environment variables (.env only)
- Passwords must be hashed (bcrypt / passlib)
- JWT must include expiration and validation checks

---

## Authentication System (Important)

- JWT-based auth using access + refresh tokens
- Access token = short-lived
- Refresh token = long-lived + revocable
- Refresh tokens should be stored in Redis or DB
- `get_current_user` should first check Redis cache before DB

---

## Redis Usage Rules

Redis must be used for:

- caching authenticated user sessions
- storing refresh tokens
- password reset tokens

All cached data MUST include TTL.

---

## Roles & Permissions (RBAC)

Supported roles:

- user
- admin

Rules:

- Only admin can perform admin-level actions
- Admin-only restrictions must be enforced via dependencies
- Role checks must NOT be duplicated in routers (use dependency layer)

Special rule:

- Only admin can change default avatar behavior (as defined in services)

---

## Password Reset Flow

Must include:

- secure token generation
- email delivery via FastAPI-Mail
- token expiration (time-limited)
- one-time usage enforcement

Never expose reset tokens in API responses.

---

## Testing Requirements

Use Pytest:

### Required coverage:

- Minimum 75% code coverage (pytest-cov)

### Test types:

- Unit tests → repositories + services
- Integration tests → API endpoints

### Rules:

- External services MUST be mocked:
  - Redis
  - Email service
  - Cloudinary
- Test structure must mirror application structure

---

## Documentation Requirements (Sphinx)

- All public functions and classes must have docstrings
- Docstrings must follow Sphinx-compatible format
- API and services must be documented
- Authentication flow must be documented

---

## Docker Requirements

- All services must run via docker-compose
- Must include:
  - API service
  - PostgreSQL
  - Redis
- All environment variables must be in .env
- No secrets in codebase

---

## Development Workflow for Copilot

When implementing features:

1. First analyze existing code (@workspace if needed)
2. Propose implementation plan
3. Wait for confirmation if task is complex
4. Implement step-by-step
5. Do NOT implement multiple features at once
6. Keep changes minimal and consistent with architecture

---

## Feature Priority Order (IMPORTANT)

When working on tasks, follow this order:

1. Security & Auth (refresh tokens, RBAC, password reset)
2. Infrastructure (Redis, config, caching)
3. Testing (unit + integration + coverage)
4. Documentation (Sphinx + docstrings)
5. Optional improvements (deployment, optimization)

---

## Non-goals

- Do not redesign architecture unless explicitly requested
- Do not refactor unrelated modules
- Do not mix layers
