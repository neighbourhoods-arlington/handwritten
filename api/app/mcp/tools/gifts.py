"""Gift tools: gifts table and the eligible_gifts() SQL function."""

from datetime import date
from decimal import Decimal
from typing import Literal

from fastmcp import FastMCP
from sqlalchemy import select, text

from app.core.db import SessionLocal
from app.mcp.tools.common import READ_ONLY, dump
from app.models import Gift
from app.schemas.gift import EligibleGiftRead, GiftRead

gifts = FastMCP("gifts")

ELIGIBLE_GIFTS_SQL = text(
    "SELECT * FROM eligible_gifts("
    " :gift_window_days, CAST(:max_amount AS numeric), :max_direct_gifts,"
    " :min_days_since_note, COALESCE(CAST(:today AS date), CURRENT_DATE))"
)


@gifts.tool(annotations=READ_ONLY)
async def list_gifts(
    donor_id: int | None = None,
    channel: Literal["direct", "raise_ride"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
) -> list[dict]:
    """List gifts, newest first. Filter by donor, channel (direct / raise_ride) and date range."""
    stmt = select(Gift)
    if donor_id is not None:
        stmt = stmt.where(Gift.donor_id == donor_id)
    if channel is not None:
        stmt = stmt.where(Gift.channel == channel)
    if date_from is not None:
        stmt = stmt.where(Gift.gift_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Gift.gift_date <= date_to)
    stmt = stmt.order_by(Gift.gift_date.desc(), Gift.gift_id.desc()).limit(limit)
    async with SessionLocal() as session:
        return [dump(GiftRead, g) for g in await session.scalars(stmt)]


@gifts.tool(annotations=READ_ONLY)
async def find_eligible_gifts(
    gift_window_days: int = 30,
    max_amount: Decimal = Decimal(100),
    max_direct_gifts: int = 3,
    min_days_since_note: int = 180,
    today: date | None = None,
) -> list[dict]:
    """This week's thank-you candidates: at most one gift per donor.

    A gift qualifies when it is a direct gift (not Raise + Ride) from the last
    gift_window_days, amount <= max_amount, the donor has <= max_direct_gifts direct
    gifts in total, has a mailing address, has no open draft/approved note, and was not
    sent a note in the last min_days_since_note days.
    """
    async with SessionLocal() as session:
        result = await session.execute(
            ELIGIBLE_GIFTS_SQL,
            {
                "gift_window_days": gift_window_days,
                "max_amount": max_amount,
                "max_direct_gifts": max_direct_gifts,
                "min_days_since_note": min_days_since_note,
                "today": today,
            },
        )
        return [dump(EligibleGiftRead, dict(row)) for row in result.mappings()]
