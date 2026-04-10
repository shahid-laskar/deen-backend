from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """All schemas inherit from this for consistent ORM mode config."""
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(AppBaseModel):
    created_at: datetime
    updated_at: datetime


class IDSchema(AppBaseModel):
    id: UUID


class MessageResponse(AppBaseModel):
    message: str


class PaginatedResponse(AppBaseModel):
    items: list
    total: int
    page: int
    per_page: int
    pages: int
