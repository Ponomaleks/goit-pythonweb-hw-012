# PROJECT CONTEXT

FastAPI backend with layered architecture:

- API layer (routers only)
- Service layer (business logic)
- Repository layer (DB access)
- Infrastructure (Redis, DB, Mail, Cloudinary)

---

## Critical rules
- services contain business logic
- repositories only DB queries
- routers must stay thin
- async everywhere