import uuid
from datetime import datetime

from pydantic import BaseModel


class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class SlotOut(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    is_booked: bool

    class Config:
        from_attributes = True
