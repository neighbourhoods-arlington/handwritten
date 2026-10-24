from datetime import date

from app.content.letters import BADGE_BY_KEY, BADGES
from app.services.badges import GiftHistory, compute_badge, is_memorial_or_honor


def history(**overrides) -> GiftHistory:
    base = dict(
        gift_id=1,
        gift_date=date(2026, 10, 21),
        direct_gift_count=2,
        nth_direct_gift=2,
        first_direct_gift_date=date(2026, 3, 1),
        previous_direct_gift_date=date(2026, 3, 1),
        days_since_previous_direct_gift=234,
        distinct_years=1,
        gives_through_raise_ride=False,
        memorial_or_honor=False,
    )
    base.update(overrides)
    return GiftHistory(**base)


def test_every_badge_rule_has_a_curated_badge():
    rules = {
        "lantern",
        "first_gear",
        "headlight",
        "spoke_star",
        "chain_keeper",
        "tailwind",
        "kickstand",
    }
    assert rules <= set(BADGE_BY_KEY)
    assert len(BADGES) == len(rules)


def test_rules_in_precedence_order():
    assert compute_badge(history(memorial_or_honor=True, nth_direct_gift=1)) == "lantern"
    assert compute_badge(history(nth_direct_gift=1, direct_gift_count=1)) == "first_gear"
    assert compute_badge(history(days_since_previous_direct_gift=400)) == "headlight"
    assert compute_badge(history(gives_through_raise_ride=True)) == "spoke_star"
    assert compute_badge(history(direct_gift_count=4, distinct_years=3)) == "chain_keeper"
    assert compute_badge(history(days_since_previous_direct_gift=20)) == "tailwind"
    assert compute_badge(history()) == "kickstand"


def test_memorial_detection():
    assert is_memorial_or_honor("In memory of my grandfather")
    assert is_memorial_or_honor("in honour of Coach Lee")
    assert not is_memorial_or_honor("Keep up the good work!")
    assert not is_memorial_or_honor(None)
