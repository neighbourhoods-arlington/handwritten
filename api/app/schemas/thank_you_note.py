from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NoteStatus = Literal["draft", "approved", "rejected", "sent"]


class ThankYouNoteCreate(BaseModel):
    donor_id: int
    gift_id: int | None = None
    batch_week: date
    body: str | None = None


class ThankYouNoteUpdate(BaseModel):
    body: str | None = None
    status: NoteStatus | None = None
    # Required by the DB when moving to "approved" or "sent"
    approved_by: str | None = Field(default=None, min_length=1)


class ThankYouNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    note_id: int
    donor_id: int
    gift_id: int | None
    batch_week: date
    body: str | None
    status: NoteStatus
    approved_by: str | None
    approved_at: datetime | None
    sent_at: datetime | None
    created_at: datetime
