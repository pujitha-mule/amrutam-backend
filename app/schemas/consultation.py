import uuid
from datetime import datetime

from pydantic import BaseModel


class BookConsultationRequest(BaseModel):
    slot_id: uuid.UUID


class ConsultationOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    slot_id: uuid.UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
