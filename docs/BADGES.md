# Badges

A badge is a small, meaning-based recognition shown on the donor's private page
(the page behind the QR code on each handwritten note). It is **never about amounts or
totals**. It tells the donor what their gift *means* to Phoenix Bikes, in bike language.

Each thank-you note gets exactly one badge. The badge is stored on the note
(`thank_you_notes.badge_key`) at the moment the letter is drafted, so it reflects the
donor's history *at that gift* and does not change later.

## How a badge is chosen

Badges are **computed by rules, not by the language model.** The rules only use facts
already in the database: gift dates, the gift channel (direct vs Raise + Ride) and the
donor's own note that came with the gift. The same history always yields the same badge,
and nothing can be invented. This follows the project rule that the LLM never invents
facts (see `CLAUDE.md`).

Implementation: `api/app/services/badges.py` (`compute_badge`, `load_gift_history`).
Titles, meanings and keys live in `api/app/content/letters.py` (`BADGES`).
Icons live in `web/src/components/badge-icon/badge-icon.tsx`.

## The seven badges

Rules are checked **from top to bottom; the first match wins.**

| # | Key | Title | Rule | Meaning shown to the donor |
|---|-----|-------|------|----------------------------|
| 1 | `lantern` | Lantern | The note that came with *this* gift says "in memory", "in loving memory", "in honor/honour", "memorial", "remembering" or "in celebration of". | Given in memory or in honor of someone: a light carried forward. |
| 2 | `first_gear` | First Gear | This is the donor's **first direct gift** ever. | Your very first gift to Phoenix Bikes. Every journey starts in first gear. |
| 3 | `headlight` | Headlight | A **returning** donor: the previous direct gift was **365 days or more** before this one. | You came back and lit the way again for the next rider. |
| 4 | `spoke_star` | Spoke Star | The donor gives directly **and** also rides in Raise + Ride. | Every spoke matters. Your support helps the whole wheel stay true. |
| 5 | `chain_keeper` | Chain Keeper | A **steady** donor: 3 or more direct gifts spread over 2 or more calendar years. | You keep things moving: a steady link between young riders and the road. |
| 6 | `tailwind` | Tailwind | A **quick follow-up**: the previous direct gift was **60 days or less** before this one. | You showed up exactly when it helped most, like a tailwind on a long climb. |
| 7 | `kickstand` | Kickstand | Everything else (a repeat donor who matches none of the above). | Quiet, dependable support that holds everything upright. |

### Why this order

- **Lantern first.** A memorial or honor gift carries the most personal meaning; it
  should never be overridden by a statistic.
- **First Gear before the history rules.** With one gift there is no "previous gift", so
  the rules below would not apply anyway; this just makes it explicit.
- **Headlight before Spoke Star and Chain Keeper.** Coming back after a year or more is
  the more remarkable story, even for a donor who also rides.
- **Chain Keeper before Tailwind.** Long-term steadiness beats a recent burst.
- **Kickstand last.** Every note gets a badge; nothing falls through.

## Thresholds

| Constant | Value | Where |
|----------|-------|-------|
| `RETURNING_AFTER_DAYS` | 365 | `api/app/services/badges.py` |
| `QUICK_FOLLOW_UP_DAYS` | 60 | `api/app/services/badges.py` |
| `STEADY_MIN_GIFTS` | 3 | `api/app/services/badges.py` |
| `STEADY_MIN_YEARS` | 2 | `api/app/services/badges.py` |

Change them there; the tests in `api/tests/test_badges.py` cover each rule and the
precedence order.

## What counts as "direct"

Only gifts with `channel = 'direct'` count toward First Gear, Headlight, Chain Keeper
and Tailwind. Raise + Ride gifts are never thanked by this tool (see the hard
requirements in `CLAUDE.md`), but they *do* count for Spoke Star, because the badge
celebrates a donor who supports the shop in both ways.

## Examples

| Donor history at the time of the gift | Badge |
|---------------------------------------|-------|
| First ever gift, note says "In memory of my grandfather" | Lantern |
| First ever gift, no note | First Gear |
| Second direct gift, 14 months after the first | Headlight |
| Fourth direct gift, also rode Raise + Ride last spring | Spoke Star |
| Twelfth monthly gift since last year, no Raise + Ride | Chain Keeper |
| Second direct gift, three weeks after the first | Tailwind |
| Second direct gift, seven months after the first | Kickstand |

## Where the badge appears

- **Letter page** (`/donors/{id}/letter/`): icon, title and meaning next to the QR code,
  so staff see what the donor will see.
- **Private donor page** (`/t/{token}/`): icon, title and meaning at the top, above the
  thank-you text. This page shows no amounts and is `noindex`.
- **MCP**: `get_gift_context(gift_id)` returns the computed badge so any client (the
  Ollama agent, Claude) sees the same answer as the web app.

## Adding a badge

1. Add the key, title and meaning to `BADGES` in `api/app/content/letters.py`.
2. Add the rule in `compute_badge` in `api/app/services/badges.py`, in the right place
   in the precedence order, and update the table in that file's docstring.
3. Add an icon case in `web/src/components/badge-icon/badge-icon.tsx` (unknown keys
   fall back to a generic rosette, so nothing breaks in between).
4. Extend `api/tests/test_badges.py` and this document.

Badges already stored on notes are not recomputed automatically. A one-off script can
re-run `compute_badge` over existing notes if the rules change.

## Current wording is a placeholder

Titles and meanings were written for the hackathon demo. The Phoenix Bikes team should
review the wording before real donors see it.
