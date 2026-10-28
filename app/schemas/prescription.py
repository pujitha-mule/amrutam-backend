import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PrescriptionCreate(BaseModel):
    medication: str = Field(min_length=1, max_length=200)
    strength: str = Field(min_length=1, max_length=50)
    dosage: str = Field(min_length=1, max_length=100)
    frequency: str = Field(min_length=1, max_length=100)
    duration: str = Field(min_length=1, max_length=100)
    instructions: str | None = None


class PrescriptionOut(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    medication: str
    strength: str
    dosage: str
    frequency: str
    duration: str
    instructions: str | None
    version: int
    issued_at: datetime

    class Config:
        from_attributes = True
