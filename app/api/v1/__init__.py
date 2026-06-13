"""API v1 routes."""

from app.api.v1.endpoints.contacts import router as contacts_router

__all__ = ["contacts_router"]
