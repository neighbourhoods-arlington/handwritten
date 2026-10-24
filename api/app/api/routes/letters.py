"""QR image for a note's share link, and the private token page data."""

import io

import segno
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.models import Donor, ThankYouNote
from app.schemas.letter import LetterBadge, PublicLetter
from app.services.letter import badge_for, impact_text_for

router = APIRouter(tags=["letters"])


def share_url(token: str) -> str:
    return f"{get_settings().web_base_url.rstrip('/')}/t/{token}/"


@router.get("/notes/{note_id}/qr.svg", include_in_schema=True)
async def note_qr(note_id: int, session: AsyncSession = Depends(get_session)) -> Response:
    """QR code (SVG) pointing at the note's private donor page."""
    note = await session.get(ThankYouNote, note_id)
    if note is None or not note.share_token:
        raise HTTPException(status_code=404, detail="Note has no share link")
    qr = segno.make(share_url(note.share_token), error="m")
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=6, border=2, dark="#1e3a8a", light=None)
    return Response(
        buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "max-age=3600"}
    )


@router.get("/public/t/{token}", response_model=PublicLetter)
async def public_letter(token: str, session: AsyncSession = Depends(get_session)) -> PublicLetter:
    """Data for the private, token-based donor page. No amounts, no gift details."""
    row = (
        await session.execute(
            select(ThankYouNote, Donor.first_name)
            .join(Donor, Donor.donor_id == ThankYouNote.donor_id)
            .where(ThankYouNote.share_token == token, ThankYouNote.status != "rejected")
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown link")
    note, first_name = row
    parts = _split_body(note.body)
    b = badge_for(note.badge_key)
    return PublicLetter(
        first_name=first_name,
        badge=LetterBadge(**b) if b else None,
        greeting=parts.get("greeting"),
        impact_text=impact_text_for(note.impact_key),
        closing=parts.get("closing"),
        status=note.status,
        donate_link=get_settings().donate_link,
    )


def _split_body(body: str | None) -> dict[str, str]:
    """Pull greeting and closing back out of an assembled body (see assemble_body)."""
    if not body:
        return {}
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    if len(paragraphs) < 3:
        return {}
    return {"greeting": paragraphs[0], "closing": paragraphs[2]}
