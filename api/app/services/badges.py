"""Badges are computed from the donor's giving history, never chosen by the LLM.

One badge per note. Rules are checked in order; the first match wins. They only use
facts already in the database (gift dates, channels, the donor's own note), so the
same history always yields the same badge and nothing is invented.

| key          | rule (first match wins)                                                   |
|--------------|---------------------------------------------------------------------------|
| lantern      | the gift's receipt note says "in memory" / "in honor" / "memorial"        |
| first_gear   | this is the donor's first direct gift                                      |
| headlight    | returning: previous direct gift was 365+ days before this one             |
| spoke_star   | gives directly AND rides Raise + Ride                                      |
| chain_keeper | steady: 3+ direct gifts spread over 2+ calendar years                      |
| tailwind     | quick follow-up: previous direct gift was within 60 days of this one      |
| kickstand    | everything else (2+ gifts, dependable)                                     |
"""

import re
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gift, ThankYouNote

MEMORIAL_RE = re.compile(
    r"\b(in (loving )?memory|in honou?r|memorial|remembering|in celebration of)\b", re.I
)
RETURNING_AFTER_DAYS = 365
QUICK_FOLLOW_UP_DAYS = 60
STEADY_MIN_GIFTS = 3
STEADY_MIN_YEARS = 2
NOTE_EXCERPT_CHARS = 200
PREVIOUS_NOTES_LIMIT = 3


@dataclass
class GiftHistory:
    """What we know about a donor at the moment of one specific gift."""

    gift_id: int
    gift_date: date
    direct_gift_count: int  # all direct gifts on file
    nth_direct_gift: int  # this gift's position by date (1 = first)
    first_direct_gift_date: date | None
    previous_direct_gift_date: date | None  # the direct gift just before this one
    days_since_previous_direct_gift: int | None
    distinct_years: int  # calendar years with at least one direct gift
    gives_through_raise_ride: bool
    memorial_or_honor: bool  # the receipt note of THIS gift
    previous_note_excerpts: list[str] = field(default_factory=list)

    @property
    def is_first_direct_gift(self) -> bool:
        return self.nth_direct_gift == 1


def is_memorial_or_honor(receipt_note: str | None) -> bool:
    return bool(receipt_note and MEMORIAL_RE.search(receipt_note))


def compute_badge(h: GiftHistory) -> str:
    """Pick the badge key for this gift from its history. See the table in the docstring."""
    if h.memorial_or_honor:
        return "lantern"
    if h.is_first_direct_gift:
        return "first_gear"
    gap = h.days_since_previous_direct_gift
    if gap is not None and gap >= RETURNING_AFTER_DAYS:
        return "headlight"
    if h.gives_through_raise_ride:
        return "spoke_star"
    if h.direct_gift_count >= STEADY_MIN_GIFTS and h.distinct_years >= STEADY_MIN_YEARS:
        return "chain_keeper"
    if gap is not None and gap <= QUICK_FOLLOW_UP_DAYS:
        return "tailwind"
    return "kickstand"


async def load_gift_history(session: AsyncSession, gift: Gift) -> GiftHistory:
    """Build the history for one gift from the donor's gifts and previous notes."""
    all_gifts = list(
        await session.scalars(
            select(Gift)
            .where(Gift.donor_id == gift.donor_id)
            .order_by(Gift.gift_date, Gift.gift_id)
        )
    )
    direct = [g for g in all_gifts if g.channel == "direct"]
    before = [g for g in direct if (g.gift_date, g.gift_id) < (gift.gift_date, gift.gift_id)]
    previous = before[-1] if before else None
    notes = list(
        await session.scalars(
            select(ThankYouNote.body)
            .where(
                ThankYouNote.donor_id == gift.donor_id,
                ThankYouNote.status != "rejected",
                ThankYouNote.body.is_not(None),
                ThankYouNote.gift_id != gift.gift_id,
            )
            .order_by(ThankYouNote.created_at.desc())
            .limit(PREVIOUS_NOTES_LIMIT)
        )
    )
    return GiftHistory(
        gift_id=gift.gift_id,
        gift_date=gift.gift_date,
        direct_gift_count=len(direct),
        nth_direct_gift=len(before) + 1,
        first_direct_gift_date=direct[0].gift_date if direct else None,
        previous_direct_gift_date=previous.gift_date if previous else None,
        days_since_previous_direct_gift=(gift.gift_date - previous.gift_date).days
        if previous
        else None,
        distinct_years=len({g.gift_date.year for g in direct}),
        gives_through_raise_ride=any(g.channel == "raise_ride" for g in all_gifts),
        memorial_or_honor=is_memorial_or_honor(gift.receipt_note),
        previous_note_excerpts=[b[:NOTE_EXCERPT_CHARS] for b in notes],
    )
