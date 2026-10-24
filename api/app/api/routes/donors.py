"""Donors page API and the "Say thank-you" action.

"Say thank-you" creates a *draft* thank_you_note for the donor's most recent direct gift
that has not been thanked yet and drafts its text with Ollama + MCP tools
(app/services/letter.py). Staff approval and export are separate steps; nothing here can
mark a note approved or sent.
"""

import secrets
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.letters import share_url
from app.core.db import get_session
from app.models import Donor, DonorSummary, Gift, ThankYouNote
from app.schemas.donor import DonorListItem, DonorListResponse
from app.schemas.letter import (
    LetterBadge,
    LetterChecks,
    LetterDonor,
    LetterGift,
    LetterNote,
    LetterResponse,
)
from app.services.badges import compute_badge, load_gift_history
from app.services.letter import GiftFacts, badge_for, generate_letter, impact_text_for

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


def _letter_response(
    note: ThankYouNote,
    gift: Gift,
    donor: Donor,
    *,
    created: bool,
    generated: bool,
    warnings: list[str],
) -> LetterResponse:
    b = badge_for(note.badge_key)
    return LetterResponse(
        note=LetterNote.model_validate(note),
        gift=LetterGift.model_validate(gift),
        donor=LetterDonor(
            donor_id=donor.donor_id,
            first_name=donor.first_name,
            last_name=donor.last_name,
            address_line=donor.address_line,
            city=donor.city,
            state=donor.state,
            zip=donor.zip,
        ),
        badge=LetterBadge(**b) if b else None,
        impact_text=impact_text_for(note.impact_key),
        share_url=share_url(note.share_token) if note.share_token else None,
        qr_url=f"/api/v1/notes/{note.note_id}/qr.svg" if note.share_token else None,
        created=created,
        generated=generated,
        needs_attention=note.body is None,
        warnings=warnings,
    )


async def _open_note(session: AsyncSession, donor_id: int) -> ThankYouNote | None:
    return await session.scalar(
        select(ThankYouNote)
        .where(ThankYouNote.donor_id == donor_id, ThankYouNote.status.in_(OPEN_STATUSES))
        .order_by(ThankYouNote.created_at.desc())
        .limit(1)
    )


async def _generate_into(
    session: AsyncSession, note: ThankYouNote, donor: Donor, gift: Gift
) -> list[str]:
    """Run the LLM for this note and store the result. Returns warnings for staff."""
    history = await load_gift_history(session, gift)
    batch_bodies = list(
        await session.scalars(
            select(ThankYouNote.body)
            .where(
                ThankYouNote.batch_week == note.batch_week,
                ThankYouNote.note_id != note.note_id,
                ThankYouNote.body.is_not(None),
            )
            .limit(100)
        )
    )
    facts = GiftFacts(
        donor_id=donor.donor_id,
        first_name=donor.first_name,
        last_name=donor.last_name,
        gift_id=gift.gift_id,
        amount=gift.amount,
        gift_date=gift.gift_date,
        fund=gift.fund,
        campaign=gift.campaign,
        receipt_note=gift.receipt_note,
        badge_key=compute_badge(history),
        direct_gift_count=history.direct_gift_count,
        nth_direct_gift=history.nth_direct_gift,
        first_direct_gift_date=history.first_direct_gift_date,
        days_since_previous_direct_gift=history.days_since_previous_direct_gift,
        gives_through_raise_ride=history.gives_through_raise_ride,
        memorial_or_honor=history.memorial_or_honor,
        previous_notes=history.previous_note_excerpts,
    )
    draft = await generate_letter(facts, batch_bodies)
    note.body = draft.body
    note.impact_key = draft.impact_key
    note.badge_key = draft.badge_key
    note.llm_model = draft.model
    note.checks = LetterChecks(
        issues=draft.issues,
        warnings=draft.warnings,
        attempts=draft.attempts,
        tool_calls=draft.tool_calls,
    ).model_dump()
    if not note.share_token:
        note.share_token = secrets.token_urlsafe(12)
    await session.commit()
    await session.refresh(note)
    return draft.warnings


@router.get("/{donor_id}/thank-you", response_model=LetterResponse)
async def get_thank_you(
    donor_id: int, session: AsyncSession = Depends(get_session)
) -> LetterResponse:
    """The donor's current (draft/approved) letter, if one exists."""
    donor = await session.get(Donor, donor_id)
    if donor is None:
        raise HTTPException(status_code=404, detail="Donor not found")
    note = await _open_note(session, donor_id)
    if note is None or note.gift_id is None:
        raise HTTPException(status_code=404, detail="No thank-you letter for this donor yet")
    gift = await session.get(Gift, note.gift_id)
    assert gift is not None
    warnings = list((note.checks or {}).get("warnings", []))
    return _letter_response(note, gift, donor, created=False, generated=False, warnings=warnings)


@router.post("/{donor_id}/thank-you", response_model=LetterResponse)
async def say_thank_you(
    donor_id: int, session: AsyncSession = Depends(get_session)
) -> LetterResponse:
    """Return the donor's existing letter, or draft a new one with Ollama + MCP tools.

    - An open note with a body is returned as is (nothing is regenerated).
    - An open note without a body ("needs attention") is regenerated.
    - Otherwise a draft note is created for the latest un-thanked direct gift and the
      letter is generated. Every refusal carries an explicit reason.
    """
    donor = await session.get(Donor, donor_id)
    if donor is None:
        raise HTTPException(status_code=404, detail="Donor not found")

    note = await _open_note(session, donor_id)
    if note is not None and note.gift_id is not None:
        gift = await session.get(Gift, note.gift_id)
        assert gift is not None
        if note.body:
            warnings = list((note.checks or {}).get("warnings", []))
            return _letter_response(
                note, gift, donor, created=False, generated=False, warnings=warnings
            )
        warnings = await _generate_into(session, note, donor, gift)
        return _letter_response(note, gift, donor, created=False, generated=True, warnings=warnings)

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
    warnings += await _generate_into(session, note, donor, gift)
    return _letter_response(note, gift, donor, created=True, generated=True, warnings=warnings)
