import uuid

from pydantic import BaseModel


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    mfa_enabled: bool

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    city: str | None = None
