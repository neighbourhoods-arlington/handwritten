from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DonorCreate(BaseModel):
    account_number: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str | None = None
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None


class DonorUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    email: str | None = None
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None


class DonorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    donor_id: int
    account_number: str
    first_name: str
    last_name: str
    email: str | None
    address_line: str | None
    city: str | None
    state: str | None
    zip: str | None
    created_at: datetime
    updated_at: datetime


class DonorSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    donor_id: int
    account_number: str
    first_name: str
    last_name: str
    gift_count: int
    direct_gift_count: int
    total_given: Decimal | None
    direct_total: Decimal | None
    last_gift_date: date | None
    raise_ride_only: bool
    last_note_sent_at: datetime | None


class DonorListItem(DonorSummaryRead):
    """One row of the Donors page: giving summary + contact + open-note state."""

    email: str | None
    city: str | None
    state: str | None
    has_address: bool
    # Open (draft/approved) note, if any — the donor is already queued for a thank-you
    pending_note_id: int | None = None
    pending_note_status: str | None = None


class DonorListResponse(BaseModel):
    items: list[DonorListItem]
    total: int
    limit: int
    offset: int
