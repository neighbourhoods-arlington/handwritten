from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GiftChannel = Literal["direct", "raise_ride"]


class ImportBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: int
    source_file: str
    imported_at: datetime
    rows_read: int
    donors_inserted: int
    gifts_inserted: int


class GiftCreate(BaseModel):
    donor_id: int
    gift_date: date
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    fund: str | None = None
    campaign: str | None = None
    appeal: str | None = None
    payment_method: str | None = None
    receipt_note: str | None = None
    source_hash: str = Field(min_length=1)
    batch_id: int | None = None


class GiftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gift_id: int
    donor_id: int
    gift_date: date
    amount: Decimal
    fund: str | None
    campaign: str | None
    appeal: str | None
    payment_method: str | None
    receipt_note: str | None
    channel: GiftChannel
    source_hash: str
    batch_id: int | None


class EligibleGiftsParams(BaseModel):
    """Arguments of the `eligible_gifts()` SQL function."""

    gift_window_days: int = Field(default=30, ge=0)
    max_amount: Decimal = Field(default=Decimal(100), gt=0)
    max_direct_gifts: int = Field(default=3, ge=0)
    min_days_since_note: int = Field(default=180, ge=0)
    today: date | None = None


class EligibleGiftRead(BaseModel):
    """One row returned by `eligible_gifts()`: the single gift to thank per donor."""

    model_config = ConfigDict(from_attributes=True)

    donor_id: int
    gift_id: int
    first_name: str
    last_name: str
    gift_date: date
    amount: Decimal
    fund: str | None
    campaign: str | None
    appeal: str | None
    receipt_note: str | None
    direct_gift_count: int
