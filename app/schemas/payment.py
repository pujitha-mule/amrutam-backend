import uuid
from datetime import datetime

from pydantic import BaseModel


class PaymentOut(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    amount: float
    currency: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
