# ACTIVE TASK

## TASK ID: SEC-001

## Title:
Role-Based Access Control (RBAC)

---

## Objective:
Introduce user roles and enforce permissions across API.

---

## Scope (STRICT)
- add role field to User model (user/admin)
- implement role check dependency
- protect admin-only operations
- enforce role validation in dependency layer (not routers)

---

## Constraints
- default role should be "user"
- only admin can change role
- no duplicated role checks in endpoints
- must use FastAPI dependencies
- no breaking API changes
- role checks must be in dependency layer

---

## Acceptance Criteria
- admin-only routes are protected
- users have assignable roles
- normal users cannot access admin actions
- role system is reusable via dependency