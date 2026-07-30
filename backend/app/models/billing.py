from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, StrictInt, field_validator, model_validator


class PaymentMode(str, Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"


class LineItem(BaseModel):
    drug_name: str = Field(min_length=1)
    qty: StrictInt = Field(gt=0)
    unit_price_paise: StrictInt = Field(ge=0)


class BillingLogEntry(BaseModel):
    clinic_id: str = Field(min_length=1)
    visit_id: str = Field(min_length=1)
    timestamp: datetime
    doctor_id: str = Field(min_length=1)
    line_items: list[LineItem] = Field(min_length=1)
    payment_mode: PaymentMode
    amount_paid_paise: StrictInt
    discount_paise: StrictInt = Field(ge=0)
    is_refund: bool

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include a UTC timezone offset (ISO8601, e.g. ...Z)")
        if value.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("timestamp must be in UTC (offset +00:00 / Z)")
        return value

    @model_validator(mode="after")
    def refund_amount_sign_matches_flag(self) -> "BillingLogEntry":
        if self.is_refund and self.amount_paid_paise > 0:
            raise ValueError(
                "is_refund is true but amount_paid_paise is positive; "
                "refund rows must have amount_paid_paise <= 0"
            )
        if not self.is_refund and self.amount_paid_paise < 0:
            raise ValueError(
                "amount_paid_paise is negative but is_refund is false; "
                "negative amounts are only valid on refund rows"
            )
        return self
