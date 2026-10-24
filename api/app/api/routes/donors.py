"""Donors page API and the "Say thank-you" action.

"Say thank-you" only creates a *draft* thank_you_note for the donor's most recent direct
gift that has not been thanked yet. Note text generation, staff approval and export are
separate steps; nothing here can mark a note approved or sent.
"""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import Donor, DonorSummary, Gift, ThankYouNote
from app.schemas.donor import DonorListItem, DonorListResponse, SayThankYouResponse

router = APIRouter(prefix="/donors", tags=["donors"])

OPEN_STATUSES = ("draft", "approved")
COOLDOWN_WARNING_DAYS = 180


def _week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _list_stmt():
    """donor_summary ⨝ donors, plus the donor's latest open (draft/approved) note."""
    latest_open = (
        select(ThankYouNote.donor_id, func.max(ThankYouNote.note_id).label("note_id"))
        .where(ThankYouNote.status.in_(OPEN_STATUSES))
        .group_by(ThankYouNote.donor_id)
        .subquery("latest_open")
    )
    return (
        select(
            DonorSummary,
            Donor.email,
            Donor.city,
            Donor.state,
            (func.coalesce(Donor.address_line, "") != "").label("has_address"),
            latest_open.c.note_id.label("pending_note_id"),
            ThankYouNote.status.label("pending_note_status"),
        )
        .join(Donor, Donor.donor_id == DonorSummary.donor_id)
        .outerjoin(latest_open, latest_open.c.donor_id == DonorSummary.donor_id)
        .outerjoin(ThankYouNote, ThankYouNote.note_id == latest_open.c.note_id)
    )


def _row_to_item(row) -> DonorListItem:
    summary: DonorSummary = row.DonorSummary
    return DonorListItem(
        **{k: getattr(summary, k) for k in DonorSummary.__table__.columns.keys()},
        email=row.email,
        city=row.city,
        state=row.state,
        has_address=row.has_address,
        pending_note_id=row.pending_note_id,
        pending_note_status=row.pending_note_status,
    )


@router.get("", response_model=DonorListResponse)
async def list_donors(
    q: str | None = Query(default=None, description="Search name, account number or email"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> DonorListResponse:
    stmt = _list_stmt()
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        full_name = DonorSummary.first_name + " " + DonorSummary.last_name
        stmt = stmt.where(
            or_(
                full_name.ilike(pattern),
                DonorSummary.account_number.ilike(pattern),
                Donor.email.ilike(pattern),
            )
        )
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await session.execute(
        stmt.order_by(DonorSummary.last_name, DonorSummary.first_name).limit(limit).offset(offset)
    )
    return DonorListResponse(
        items=[_row_to_item(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.get("/{donor_id}", response_model=DonorListItem)
async def get_donor(donor_id: int, session: AsyncSession = Depends(get_session)) -> DonorListItem:
    row = (await session.execute(_list_stmt().where(DonorSummary.donor_id == donor_id))).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Donor not found")
    return _row_to_item(row)


@router.post(
    "/{donor_id}/thank-you",
    response_model=SayThankYouResponse,
    status_code=status.HTTP_201_CREATED,
)
async def say_thank_you(
    donor_id: int, session: AsyncSession = Depends(get_session)
) -> SayThankYouResponse:
    """Create a draft thank-you note for the donor's latest un-thanked direct gift.

    Every refusal carries an explicit reason so staff can see why.
    """
    if await session.get(Donor, donor_id) is None:
        raise HTTPException(status_code=404, detail="Donor not found")

    open_note = await session.scalar(
        select(ThankYouNote)
        .where(ThankYouNote.donor_id == donor_id, ThankYouNote.status.in_(OPEN_STATUSES))
        .order_by(ThankYouNote.created_at.desc())
        .limit(1)
    )
    if open_note is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Donor already has a {open_note.status} note (#{open_note.note_id}). "
            "Review it before creating another.",
        )

    has_active_note = exists().where(
        ThankYouNote.gift_id == Gift.gift_id, ThankYouNote.status != "rejected"
    )
    gift = await session.scalar(
        select(Gift)
        .where(Gift.donor_id == donor_id, Gift.channel == "direct", ~has_active_note)
        .order_by(Gift.gift_date.desc(), Gift.amount.desc())
        .limit(1)
    )
    if gift is None:
        direct_count = await session.scalar(
            select(func.count()).where(Gift.donor_id == donor_id, Gift.channel == "direct")
        )
        raise HTTPException(
            status_code=409,
            detail=(
                "Donor has only given through Raise + Ride; there is no direct gift to thank."
                if not direct_count
                else "Every direct gift from this donor already has a thank-you note."
            ),
        )

    warnings: list[str] = []
    last_sent = await session.scalar(
        select(func.max(ThankYouNote.sent_at)).where(
            ThankYouNote.donor_id == donor_id, ThankYouNote.status == "sent"
        )
    )
    if last_sent is not None:
        days = (datetime.now(UTC) - last_sent).days
        if days < COOLDOWN_WARNING_DAYS:
            warnings.append(
                f"Last thank-you was sent {days} days ago "
                f"(cooldown is {COOLDOWN_WARNING_DAYS} days)."
            )

    note = ThankYouNote(
        donor_id=donor_id,
        gift_id=gift.gift_id,
        batch_week=_week_monday(date.today()),
        status="draft",
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return SayThankYouResponse(
        note_id=note.note_id,
        status=note.status,
        batch_week=note.batch_week,
        gift_id=gift.gift_id,
        gift_date=gift.gift_date,
        amount=gift.amount,
        warnings=warnings,
    )
