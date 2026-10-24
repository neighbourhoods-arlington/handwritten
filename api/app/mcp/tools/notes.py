"""Thank-you note tools: draft → approved → sent (or rejected).

The agent may write and edit drafts. Approving and marking as sent are tagged
STAFF: the schema requires approved_by, i.e. a person signed off on the note.
"""

from datetime import UTC, date, datetime, timedelta

from fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.mcp.tools.common import READ_ONLY, STAFF, dump
from app.models import Donor, Gift, ThankYouNote
from app.schemas.gift import GiftRead
from app.schemas.thank_you_note import NoteStatus, ThankYouNoteRead

notes = FastMCP("notes")


def week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


async def _get_note(session: AsyncSession, note_id: int) -> ThankYouNote:
    note = await session.get(ThankYouNote, note_id)
    if note is None:
        raise ValueError(f"Note {note_id} not found")
    return note


def _require_status(note: ThankYouNote, *allowed: str) -> None:
    if note.status not in allowed:
        raise ValueError(
            f"Note {note.note_id} is '{note.status}'; this needs status {' or '.join(allowed)}"
        )


@notes.tool(annotations=READ_ONLY)
async def list_notes(
    status: NoteStatus | None = None,
    batch_week: date | None = None,
    donor_id: int | None = None,
    limit: int = 50,
) -> list[dict]:
    """List thank-you notes, newest first. batch_week is the Monday of the note's week."""
    stmt = select(ThankYouNote, Donor.first_name, Donor.last_name).join(Donor)
    if status is not None:
        stmt = stmt.where(ThankYouNote.status == status)
    if batch_week is not None:
        stmt = stmt.where(ThankYouNote.batch_week == week_monday(batch_week))
    if donor_id is not None:
        stmt = stmt.where(ThankYouNote.donor_id == donor_id)
    stmt = stmt.order_by(ThankYouNote.created_at.desc()).limit(limit)
    async with SessionLocal() as session:
        result = await session.execute(stmt)
        return [
            dump(ThankYouNoteRead, note) | {"donor_name": f"{first} {last}"}
            for note, first, last in result
        ]


@notes.tool(annotations=READ_ONLY)
async def get_note(note_id: int) -> dict:
    """Get one thank-you note with the donor's name/address and the gift it thanks."""
    async with SessionLocal() as session:
        note = await _get_note(session, note_id)
        donor = await session.get(Donor, note.donor_id)
        gift = await session.get(Gift, note.gift_id) if note.gift_id else None
        return {
            "note": dump(ThankYouNoteRead, note),
            "donor": {
                "donor_id": donor.donor_id,
                "name": f"{donor.first_name} {donor.last_name}",
                "address_line": donor.address_line,
                "city": donor.city,
                "state": donor.state,
                "zip": donor.zip,
            },
            "gift": dump(GiftRead, gift) if gift else None,
        }


@notes.tool
async def create_note_draft(
    donor_id: int, body: str, gift_id: int | None = None, batch_week: date | None = None
) -> dict:
    """Create a draft thank-you note for a donor, usually for a gift from find_eligible_gifts.

    batch_week defaults to the Monday of the current week. A gift can have only one
    note that is not rejected.
    """
    async with SessionLocal() as session:
        if await session.get(Donor, donor_id) is None:
            raise ValueError(f"Donor {donor_id} not found")
        if gift_id is not None:
            gift = await session.get(Gift, gift_id)
            if gift is None or gift.donor_id != donor_id:
                raise ValueError(f"Gift {gift_id} not found for donor {donor_id}")
        note = ThankYouNote(
            donor_id=donor_id,
            gift_id=gift_id,
            batch_week=week_monday(batch_week or date.today()),
            body=body,
        )
        session.add(note)
        try:
            await session.commit()
        except IntegrityError as exc:
            raise ValueError(f"Gift {gift_id} already has an active note") from exc
        await session.refresh(note)
        return dump(ThankYouNoteRead, note)


@notes.tool
async def update_note_draft(note_id: int, body: str) -> dict:
    """Replace the text of a draft note. Approved or sent notes cannot be edited."""
    async with SessionLocal() as session:
        note = await _get_note(session, note_id)
        _require_status(note, "draft")
        note.body = body
        await session.commit()
        await session.refresh(note)
        return dump(ThankYouNoteRead, note)


@notes.tool
async def reject_note(note_id: int) -> dict:
    """Reject a draft or approved note. Its gift can then get a new draft."""
    async with SessionLocal() as session:
        note = await _get_note(session, note_id)
        _require_status(note, "draft", "approved")
        note.status = "rejected"
        await session.commit()
        await session.refresh(note)
        return dump(ThankYouNoteRead, note)


@notes.tool(tags={STAFF})
async def approve_note(note_id: int, approved_by: str) -> dict:
    """Staff only: approve a draft note. approved_by is the staff member's name."""
    if not approved_by.strip():
        raise ValueError("approved_by is required")
    async with SessionLocal() as session:
        note = await _get_note(session, note_id)
        _require_status(note, "draft")
        note.status = "approved"
        note.approved_by = approved_by.strip()
        note.approved_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(note)
        return dump(ThankYouNoteRead, note)


@notes.tool(tags={STAFF})
async def mark_note_sent(note_id: int, sent_at: datetime | None = None) -> dict:
    """Staff only: mark an approved note as mailed. sent_at defaults to now."""
    async with SessionLocal() as session:
        note = await _get_note(session, note_id)
        _require_status(note, "approved")
        note.status = "sent"
        note.sent_at = sent_at or datetime.now(UTC)
        await session.commit()
        await session.refresh(note)
        return dump(ThankYouNoteRead, note)
