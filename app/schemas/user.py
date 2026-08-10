import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from app.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = Field(default=UserRole.ATTENDEE)

    @field_validator("password")
    @classmethod
    def password_must_have_letter_and_digit(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Parola trebuie să conțină cel puțin o cifră")
        if not any(c.isalpha() for c in v):
            raise ValueError("Parola trebuie să conțină cel puțin o literă")
        return v

    @field_validator("role")
    @classmethod
    def no_public_admin_registration(cls, v: UserRole) -> UserRole:
        if v == UserRole.ADMIN:
            raise ValueError("Rolul admin nu poate fi atribuit prin înregistrare publică")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None


class UserAdminUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRole
    is_active: bool
    created_at: datetime