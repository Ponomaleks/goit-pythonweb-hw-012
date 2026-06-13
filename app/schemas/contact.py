"""Pydantic schemas for contacts."""

from datetime import date, datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    JsonValue,
    field_validator,
)


def validate_email_length(value: EmailStr) -> EmailStr:
    """Ensure email length does not exceed database column size."""

    if len(value) > 255:
        raise ValueError("Too long email")
    return value


class BaseSchema(BaseModel):
    """Base schema config shared by all API schemas."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )


FirstName = Annotated[str, Field(min_length=1, max_length=100)]
LastName = Annotated[str, Field(min_length=1, max_length=100)]
Email = Annotated[
    EmailStr,
    AfterValidator(validate_email_length),
]
PhoneNumber = Annotated[
    str,
    Field(min_length=5, max_length=32, pattern=r"^\+?[0-9\s\-]{5,32}$"),
]
AdditionalData = dict[str, JsonValue] | None


class BirthdayValidationMixin:
    @field_validator("birthday")
    @classmethod
    def validate_birthday_not_future(cls, value: date | None):
        if value is not None and value > date.today():
            raise ValueError("Birthday cannot be in the future")
        return value


class ContactBase(BaseSchema, BirthdayValidationMixin):
    """Shared contact fields used by create and update schemas."""

    first_name: FirstName
    last_name: LastName
    email: Email
    phone_number: PhoneNumber
    birthday: date
    additional_data: AdditionalData = None


class ContactCreate(ContactBase):
    """Payload used to create a new contact."""


class ContactUpdate(BaseSchema, BirthdayValidationMixin):
    """Payload used to partially update an existing contact."""

    first_name: FirstName | None = None
    last_name: LastName | None = None
    email: Email | None = None
    phone_number: PhoneNumber | None = None
    birthday: date | None = None
    additional_data: AdditionalData = None


class ContactResponse(ContactBase):
    """Contact representation returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime


class ContactSearchQuery(BaseSchema):
    """Query parameters used to search contacts."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=1, max_length=255)


class UpcomingBirthdayResponse(BaseSchema):
    """Contact representation used in the upcoming birthdays response."""

    id: int
    first_name: str
    last_name: str
    birthday: date
