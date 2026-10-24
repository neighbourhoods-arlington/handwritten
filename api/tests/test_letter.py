from datetime import date
from decimal import Decimal

from app.content.letters import BADGES, IMPACT_BY_KEY, IMPACT_OPTIONS
from app.services.letter import GiftFacts, LetterJSON, assemble_body, check_body, money

FACTS = GiftFacts(
    donor_id=1,
    first_name="Maya",
    last_name="Chen",
    gift_id=10,
    amount=Decimal("35.00"),
    gift_date=date(2026, 10, 21),
    fund="Earn-A-Bike",
)


def test_curated_lists_are_non_empty_and_unique():
    assert IMPACT_OPTIONS and BADGES
    assert len({o["key"] for o in IMPACT_OPTIONS}) == len(IMPACT_OPTIONS)
    assert len({b["key"] for b in BADGES}) == len(BADGES)


def test_schema_only_accepts_curated_keys():
    ok = LetterJSON.model_validate(
        {
            "greeting": "Dear Maya,",
            "gift_thanks": "Thank you for your $35 gift to Earn-A-Bike this week.",
            "closing": "With gratitude, the Phoenix Bikes team",
            "impact_key": "earn_a_bike",
        }
    )
    assert ok.impact_key == "earn_a_bike"
    try:
        LetterJSON.model_validate({**ok.model_dump(), "impact_key": "made_up"})
    except Exception as exc:
        assert "impact_key" in str(exc)
    else:
        raise AssertionError("invented impact_key was accepted")


def test_assembled_body_passes_checks():
    body = assemble_body(
        "Dear Maya,",
        "Thank you for your $35 gift to Earn-A-Bike this week.",
        "earn_a_bike",
        "With gratitude, the Phoenix Bikes team",
    )
    assert IMPACT_BY_KEY["earn_a_bike"]["text"] in body
    assert "phoenixbikes.org/donate" in body
    issues, warnings = check_body(body, FACTS, [])
    assert issues == [] and warnings == []


def test_checks_catch_invented_amount_and_missing_name():
    body = assemble_body(
        "Dear friend,",
        "Thank you for your $50 gift.",
        "earn_a_bike",
        "With gratitude, the Phoenix Bikes team",
    )
    issues, _ = check_body(body, FACTS, [])
    assert any("Maya" in i for i in issues)
    assert any("$35" in i for i in issues)
    assert any("$50.00" in i for i in issues)


def test_similarity_is_a_warning_not_an_issue():
    body = assemble_body(
        "Dear Maya,",
        "Thank you for your $35 gift to Earn-A-Bike this week.",
        "earn_a_bike",
        "With gratitude, the Phoenix Bikes team",
    )
    issues, warnings = check_body(body, FACTS, [body])
    assert issues == []
    assert warnings and "similar" in warnings[0]


def test_money_format():
    assert money(Decimal("35.00")) == "$35"
    assert money(Decimal("1250.50")) == "$1,250.50"


def test_repeating_the_impact_statement_is_an_issue():
    impact = IMPACT_BY_KEY["earn_a_bike"]["text"]
    body = assemble_body(
        "Dear Maya,",
        "Thank you for your $35 gift to Earn-A-Bike this week.",
        "earn_a_bike",
        f"{impact} With gratitude, the Phoenix Bikes team",
    )
    issues, _ = check_body(body, FACTS, [], "earn_a_bike")
    assert any("Repeats the impact" in i for i in issues)
