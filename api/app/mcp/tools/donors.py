"""Donor tools: donors table and the donor_summary view."""

from decimal import Decimal

from fastmcp import FastMCP
from sqlalchemy import or_, select

from app.core.db import SessionLocal
from app.mcp.tools.common import READ_ONLY, dump
from app.models import Donor, DonorSummary, Gift, ThankYouNote
from app.schemas.donor import DonorRead, DonorSummaryRead
from app.schemas.gift import GiftRead
from app.schemas.thank_you_note import ThankYouNoteRead

donors = FastMCP("donors")


@donors.tool(annotations=READ_ONLY)
async def search_donors(query: str, limit: int = 10) -> list[dict]:
    """Search donors by name, email or Bloomerang account number (case-insensitive)."""
    pattern = f"%{query}%"
    full_name = Donor.first_name + " " + Donor.last_name
    async with SessionLocal() as session:
        result = await session.execute(
            select(Donor)
            .where(
                or_(
                    full_name.ilike(pattern),
                    Donor.email.ilike(pattern),
                    Donor.account_number.ilike(pattern),
                )
            )
            .order_by(Donor.last_name, Donor.first_name)
            .limit(limit)
        )
        return [
            {
                "donor_id": d.donor_id,
                "account_number": d.account_number,
                "name": f"{d.first_name} {d.last_name}",
                "email": d.email,
                "city": d.city,
                "has_address": bool(d.address_line),
            }
            for d in result.scalars()
        ]


@donors.tool(annotations=READ_ONLY)
async def get_donor(donor_id: int, gift_limit: int = 20) -> dict:
    """Get a donor with their giving summary, most recent gifts and all thank-you notes."""
    async with SessionLocal() as session:
        donor = await session.get(Donor, donor_id)
        if donor is None:
            raise ValueError(f"Donor {donor_id} not found")
        summary = await session.get(DonorSummary, donor_id)
        gifts = await session.scalars(
            select(Gift)
            .where(Gift.donor_id == donor_id)
            .order_by(Gift.gift_date.desc())
            .limit(gift_limit)
        )
        notes = await session.scalars(
            select(ThankYouNote)
            .where(ThankYouNote.donor_id == donor_id)
            .order_by(ThankYouNote.created_at.desc())
        )
        return {
            "donor": dump(DonorRead, donor),
            "summary": dump(DonorSummaryRead, summary),
            "gifts": [dump(GiftRead, g) for g in gifts],
            "notes": [dump(ThankYouNoteRead, n) for n in notes],
        }


@donors.tool
async def update_donor_address(
    donor_id: int,
    address_line: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip: str | None = None,
) -> dict:
    """Update a donor's mailing address. Only the fields given are changed.

    Donors without an address_line never show up in find_eligible_gifts.
    """
    changes = {
        k: v
        for k, v in {"address_line": address_line, "city": city, "state": state, "zip": zip}.items()
        if v is not None
    }
    if not changes:
        raise ValueError("Give at least one of address_line, city, state, zip")
    async with SessionLocal() as session:
        donor = await session.get(Donor, donor_id)
        if donor is None:
            raise ValueError(f"Donor {donor_id} not found")
        for field, value in changes.items():
            setattr(donor, field, value)
        await session.commit()
        await session.refresh(donor)
        return dump(DonorRead, donor)


@donors.tool(annotations=READ_ONLY)
async def get_donor_summary(donor_id: int) -> dict:
    """Giving totals for one donor: gift counts, direct vs Raise + Ride, last gift, last note."""
    async with SessionLocal() as session:
        summary = await session.get(DonorSummary, donor_id)
        if summary is None:
            raise ValueError(f"Donor {donor_id} not found")
        return dump(DonorSummaryRead, summary)


@donors.tool(annotations=READ_ONLY)
async def list_donor_summaries(
    raise_ride_only: bool | None = None,
    min_direct_gifts: int | None = None,
    max_direct_gifts: int | None = None,
    min_total_given: Decimal | None = None,
    limit: int = 50,
) -> list[dict]:
    """List donor giving summaries, newest gift first, with optional filters.

    raise_ride_only=true → donors who only gave through the Raise + Ride campaign.
    """
    stmt = select(DonorSummary)
    if raise_ride_only is not None:
        stmt = stmt.where(DonorSummary.raise_ride_only.is_(raise_ride_only))
    if min_direct_gifts is not None:
        stmt = stmt.where(DonorSummary.direct_gift_count >= min_direct_gifts)
    if max_direct_gifts is not None:
        stmt = stmt.where(DonorSummary.direct_gift_count <= max_direct_gifts)
    if min_total_given is not None:
        stmt = stmt.where(DonorSummary.total_given >= min_total_given)
    stmt = stmt.order_by(DonorSummary.last_gift_date.desc().nulls_last()).limit(limit)
    async with SessionLocal() as session:
        return [dump(DonorSummaryRead, s) for s in await session.scalars(stmt)]
