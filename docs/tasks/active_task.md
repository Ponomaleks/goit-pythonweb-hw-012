# ACTIVE TASK

## TASK ID: INF-001

## Title:
Redis Caching Layer for Authenticated Users

---

## Objective:
Optimize authentication by caching current user in Redis.

---

## Scope (STRICT)
- cache user after authentication
- modify get_current_user to check Redis first
- fallback to DB if cache miss occurs
- define TTL (e.g. 15 minutes)
- ensure cache invalidation on logout or token expiry

---

## Constraints
- must not break auth flow
- must be transparent to API layer
- Redis is optional fallback-safe (system must work without it)

---

## Acceptance Criteria
- DB is not hit on cache hit
- user session is cached
- cache expires correctly