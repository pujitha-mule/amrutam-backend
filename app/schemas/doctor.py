import uuid

from pydantic import BaseModel


class DoctorOut(BaseModel):
    id: uuid.UUID
    specialty: str
    city: str
    languages: list[str]
    consultation_type: str
    is_verified: bool

    class Config:
        from_attributes = True
