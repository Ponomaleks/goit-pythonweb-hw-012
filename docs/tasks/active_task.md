# ACTIVE TASK

## TASK ID: AUTH-001

## Title:
JWT Refresh Token System

---

## Objective:
Implement secure refresh token mechanism alongside existing JWT authentication.

---

## Scope (STRICT)
- generate access_token (short-lived)
- generate refresh_token (long-lived)
- store refresh_token in Redis (or DB fallback if needed)
- implement refresh endpoint: /auth/refresh
- implement token rotation (invalidate old refresh token)

---

## Constraints
- do NOT break existing login endpoint
- do NOT modify API response structure unless necessary
- keep backward compatibility

---

## Acceptance Criteria
- user can refresh expired access token
- old refresh token becomes invalid after use
- refresh token stored securely