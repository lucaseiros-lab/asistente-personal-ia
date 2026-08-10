import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    project_id: uuid.UUID | None = None
    amount: Decimal
    currency: str = Field(default="ARS", min_length=3, max_length=3)
    category: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)
    expense_date: date


class ExpenseUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=500)
    project_id: uuid.UUID | None = None
    amount: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    category: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)
    expense_date: date | None = None


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    project_id: uuid.UUID | None
    amount: Decimal
    currency: str
    category: str | None
    notes: str | None
    expense_date: date
    created_at: datetime
    updated_at: datetime
