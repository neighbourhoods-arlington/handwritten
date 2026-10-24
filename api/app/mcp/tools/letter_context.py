"""Letter context tool: everything needed to draft a thank-you for ONE gift.

Unlike get_donor (full dump for humans and Claude), this returns only what the letter
agent should look at: the target gift, who gave it, a compact giving history, short
excerpts of previous notes (so the new one is different) and the badge computed from
that history. Other gifts' amounts are deliberately left out.
"""

from fastmcp import FastMCP

from app.content.letters import BADGE_BY_KEY
from app.core.db import SessionLocal
from app.mcp.tools.common import READ_ONLY
from app.models import Donor, Gift
from app.services.badges import compute_badge, load_gift_history

letter_context = FastMCP("letter_context")


def _money(amount) -> str:
    return f"${amount:,.2f}".replace(".00", "")


@letter_context.tool(annotations=READ_ONLY)
async def get_gift_context(gift_id: int) -> dict:
    """Facts for drafting a thank-you note for one specific gift.

    Returns the gift (amount, date, fund, the donor's own note), the donor's name, a
    compact history (first gift? returning? how many direct gifts, since when), short
    excerpts of previous thank-you notes to avoid repeating, and the badge chosen from
    that history. Use this instead of get_donor when writing a note.
    """
    async with SessionLocal() as session:
        gift = await session.get(Gift, gift_id)
        if gift is None:
            raise ValueError(f"Gift {gift_id} not found")
        donor = await session.get(Donor, gift.donor_id)
        assert donor is not None
        h = await load_gift_history(session, gift)
        badge = BADGE_BY_KEY[compute_badge(h)]
        return {
            "gift": {
                "gift_id": gift.gift_id,
                "amount": _money(gift.amount),
                "gift_date": gift.gift_date.isoformat(),
                "fund": gift.fund,
                "campaign": gift.campaign,
                "appeal": gift.appeal,
                "donor_wrote": gift.receipt_note,
                "channel": gift.channel,
            },
            "donor": {
                "donor_id": donor.donor_id,
                "first_name": donor.first_name,
                "last_name": donor.last_name,
                "city": donor.city,
                "state": donor.state,
            },
            "history": {
                "is_first_direct_gift": h.is_first_direct_gift,
                "nth_direct_gift": h.nth_direct_gift,
                "direct_gift_count": h.direct_gift_count,
                "first_direct_gift_date": h.first_direct_gift_date.isoformat()
                if h.first_direct_gift_date
                else None,
                "previous_direct_gift_date": h.previous_direct_gift_date.isoformat()
                if h.previous_direct_gift_date
                else None,
                "days_since_previous_direct_gift": h.days_since_previous_direct_gift,
                "years_with_a_gift": h.distinct_years,
                "also_rides_raise_ride": h.gives_through_raise_ride,
                "gift_is_in_memory_or_honor": h.memorial_or_honor,
            },
            "previous_notes": h.previous_note_excerpts,
            "badge": badge,
        }
