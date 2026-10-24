"""Draft a personal thank-you letter for one gift with Ollama + MCP tools.

Flow (CLAUDE.md "Non-negotiable AI safety rules"):
  1. The agent (app/services/agent.py) gathers facts through the get_gift_context MCP
     tool: the one gift being thanked, the donor's note with it, a compact giving
     history and excerpts of previous thank-you notes (to avoid repeating).
  2. The model answers with structured JSON: greeting, gift_thanks, closing, plus an
     impact_key chosen from the curated list. It never writes the impact statement
     itself. The badge is NOT chosen by the model: app/services/badges.py computes it
     from the donor's history.
  3. We assemble the body, append the donate link, and run checks: first name present,
     the only dollar amount mentioned is the gift's, link present, no placeholders,
     fits one card. A failed check is retried once with the errors fed back and
     `format=<json schema>` forcing valid JSON. If it fails again the note is left
     without a body ("needs attention") — bad output never goes downstream.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, create_model

from app.content.letters import BADGE_BY_KEY, IMPACT_BY_KEY, IMPACT_OPTIONS
from app.core.config import get_settings
from app.services.agent import run_agent
from app.services.ollama_client import get_ollama

DOLLAR_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d{1,2})?)")
PLACEHOLDER_RE = re.compile(r"[\[\]{}<>]")


@dataclass
class GiftFacts:
    donor_id: int
    first_name: str
    last_name: str
    gift_id: int
    amount: Decimal
    gift_date: date
    fund: str | None = None
    campaign: str | None = None
    receipt_note: str | None = None
    badge_key: str = "kickstand"  # computed by app/services/badges.py, not by the model
    direct_gift_count: int = 1
    nth_direct_gift: int = 1
    first_direct_gift_date: date | None = None
    days_since_previous_direct_gift: int | None = None
    gives_through_raise_ride: bool = False
    memorial_or_honor: bool = False
    previous_notes: list[str] = field(default_factory=list)


@dataclass
class LetterDraft:
    body: str | None
    greeting: str | None
    gift_thanks: str | None
    closing: str | None
    impact_key: str | None
    badge_key: str | None
    model: str
    issues: list[str]
    warnings: list[str]
    attempts: int
    tool_calls: list[str]


def _letter_schema() -> type[BaseModel]:
    impact_keys = tuple(o["key"] for o in IMPACT_OPTIONS)
    return create_model(
        "LetterJSON",
        greeting=(str, Field(min_length=3, description='e.g. "Dear Maya,"')),
        gift_thanks=(
            str,
            Field(min_length=20, description="1-2 sentences thanking for this specific gift"),
        ),
        closing=(
            str,
            Field(
                min_length=10,
                description=(
                    '1-2 warm sentences ending with "With gratitude, the Phoenix Bikes team"'
                ),
            ),
        ),
        impact_key=(Literal[impact_keys], ...),  # type: ignore[valid-type]
    )


LetterJSON = _letter_schema()


def money(amount: Decimal) -> str:
    return f"${amount:,.2f}".replace(".00", "")


def assemble_body(greeting: str, gift_thanks: str, impact_key: str, closing: str) -> str:
    s = get_settings()
    impact = IMPACT_BY_KEY[impact_key]["text"]
    return (
        f"{greeting.strip()}\n\n"
        f"{gift_thanks.strip()} {impact}\n\n"
        f"{closing.strip()}\n\n"
        f"See what your gift makes possible: {s.donate_link}"
    )


def check_body(
    body: str, facts: GiftFacts, batch_bodies: list[str], facts_impact_key: str | None = None
) -> tuple[list[str], list[str]]:
    """Return (issues, warnings). Issues block; warnings are shown to staff."""
    s = get_settings()
    issues: list[str] = []
    warnings: list[str] = []

    if facts.first_name not in body:
        issues.append(f"Donor first name '{facts.first_name}' is missing.")
    amounts = {Decimal(m.replace(",", "")) for m in DOLLAR_RE.findall(body)}
    if facts.amount not in amounts:
        issues.append(f"The gift amount {money(facts.amount)} is not mentioned.")
    for other in sorted(amounts - {facts.amount}):
        issues.append(f"Mentions ${other:,.2f}, which is not in the data.")
    if s.donate_link not in body:
        issues.append(f"Missing {s.donate_link}.")
    if PLACEHOLDER_RE.search(body):
        issues.append("Contains a leftover placeholder bracket.")
    impact = IMPACT_BY_KEY[facts_impact_key]["text"] if facts_impact_key else None
    if impact and body.count(impact) > 1:
        issues.append("Repeats the impact statement; it is added once automatically.")
    if len(body) > s.letter_max_chars:
        issues.append(f"Too long for one card ({len(body)}/{s.letter_max_chars} characters).")

    for other in batch_bodies:
        ratio = SequenceMatcher(None, body, other).ratio()
        if ratio >= s.letter_similarity_threshold:
            warnings.append(f"Very similar ({ratio:.0%}) to another note in this batch.")
            break
    return issues, warnings


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def _system_prompt() -> str:
    s = get_settings()
    impacts = "\n".join(f'  - {o["key"]}: "{o["text"]}"' for o in IMPACT_OPTIONS)
    return (
        "You draft short handwritten thank-you notes for Phoenix Bikes, a youth bike shop.\n"
        "Each note thanks ONE specific gift. First call the get_gift_context tool with the "
        "given gift_id. It returns that gift (amount, date, fund, what the donor wrote), the "
        "donor's name and a short giving history (first gift? returning after a long time? "
        "how many direct gifts, since which year), plus excerpts of previous notes.\n"
        "Use only facts returned by the tool. Mention only this gift's amount, never other "
        "amounts or totals. Never invent programs, numbers, events or quotes.\n"
        "Make the note personal: refer to the fund, to what the donor wrote, to a first gift "
        "or to a return after a long time. Do not repeat the previous notes.\n"
        f"Keep it under {s.letter_max_chars // 5} words in total. No subject line.\n\n"
        "When you have the facts, reply with ONLY a JSON object with these keys:\n"
        '  greeting: e.g. "Dear Maya,"\n'
        "  gift_thanks: 1-2 sentences thanking for this exact gift; mention the amount as "
        '"$N" exactly as returned by the tool and what it was for if the fund says so\n'
        "  impact_key: one key from the impact list below. Its text is inserted for you, "
        "so never write the impact sentence yourself in gift_thanks or closing\n"
        '  closing: 1-2 warm sentences ending with "With gratitude, the Phoenix Bikes team"\n\n'
        f"Impact options:\n{impacts}\n"
    )


def _history_line(facts: GiftFacts) -> str:
    if facts.nth_direct_gift <= 1:
        return "This is the donor's first direct gift."
    since = f" since {facts.first_direct_gift_date.year}" if facts.first_direct_gift_date else ""
    line = f"Returning donor: direct gift number {facts.nth_direct_gift}{since}."
    gap = facts.days_since_previous_direct_gift
    if gap is not None:
        line += f" Their previous direct gift was {gap} days before this one."
    if facts.gives_through_raise_ride:
        line += " They also take part in Raise + Ride."
    return line


def _task_prompt(facts: GiftFacts) -> str:
    extra = _history_line(facts) + "\n"
    if facts.receipt_note:
        extra += f"The donor wrote with the gift: {facts.receipt_note!r}\n"
    if facts.previous_notes:
        extra += f"They already received {len(facts.previous_notes)} note(s); do not repeat them.\n"
    return (
        f"Draft the note for gift_id={facts.gift_id} from {facts.first_name} {facts.last_name} "
        f"(donor_id={facts.donor_id}): {money(facts.amount)} on {facts.gift_date.isoformat()}"
        f"{' to ' + facts.fund if facts.fund else ''}.\n{extra}"
        f"Call get_gift_context(gift_id={facts.gift_id}) first, then answer with the JSON object."
    )


async def generate_letter(facts: GiftFacts, batch_bodies: list[str]) -> LetterDraft:
    s = get_settings()
    model = s.ollama_model
    issues: list[str] = []
    warnings: list[str] = []
    tool_names: list[str] = []

    # Attempt 1: agent gathers facts via MCP tools and answers with JSON
    result = await run_agent(
        [{"role": "user", "content": _task_prompt(facts)}],
        system=_system_prompt(),
        max_steps=4,
    )
    tool_names = [t.name for t in result.tool_calls]
    history = result.messages
    candidate = result.content
    attempts = 0

    for attempt in (1, 2):
        attempts = attempt
        body: str | None = None
        try:
            parsed = LetterJSON.model_validate(_extract_json(candidate) or {})
            body = assemble_body(
                parsed.greeting,  # type: ignore[attr-defined]
                parsed.gift_thanks,  # type: ignore[attr-defined]
                parsed.impact_key,  # type: ignore[attr-defined]
                parsed.closing,  # type: ignore[attr-defined]
            )
            issues, warnings = check_body(
                body,
                facts,
                batch_bodies,
                parsed.impact_key,  # type: ignore[attr-defined]
            )
        except ValidationError as exc:
            issues = [f"Invalid JSON from the model: {exc.errors()[0]['msg']}"]

        if body is not None and not issues:
            return LetterDraft(
                body=body,
                greeting=parsed.greeting,  # type: ignore[attr-defined]
                gift_thanks=parsed.gift_thanks,  # type: ignore[attr-defined]
                closing=parsed.closing,  # type: ignore[attr-defined]
                impact_key=parsed.impact_key,  # type: ignore[attr-defined]
                badge_key=facts.badge_key,
                model=model,
                issues=[],
                warnings=warnings,
                attempts=attempts,
                tool_calls=tool_names,
            )
        if attempt == 2:
            break

        # Retry once: feed the problems back and force the JSON schema
        history = history + [
            {
                "role": "user",
                "content": "Your note was rejected: "
                + " ".join(issues)
                + f" Rewrite it. Use the amount {money(facts.amount)} and the first name "
                f"{facts.first_name} exactly. Reply with the JSON object only.",
            }
        ]
        resp = await get_ollama().chat(
            model=model,
            messages=history,
            format=LetterJSON.model_json_schema(),
            stream=False,
        )
        candidate = resp.message.content or ""

    return LetterDraft(
        body=None,
        greeting=None,
        gift_thanks=None,
        closing=None,
        impact_key=None,
        badge_key=facts.badge_key,
        model=model,
        issues=issues,
        warnings=warnings,
        attempts=attempts,
        tool_calls=tool_names,
    )


def badge_for(key: str | None) -> dict[str, str] | None:
    return BADGE_BY_KEY.get(key) if key else None


def impact_text_for(key: str | None) -> str | None:
    return IMPACT_BY_KEY[key]["text"] if key in IMPACT_BY_KEY else None
