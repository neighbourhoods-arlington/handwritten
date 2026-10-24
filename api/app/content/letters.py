"""Curated text the LLM may choose from but never invent.

IMPACT_OPTIONS are the only impact statements allowed in a note (CLAUDE.md: "The LLM
never invents facts"). BADGES are the "creative badges" for the private donor page:
meaning-based, never about amounts. Which badge a note gets is decided by rules on the
donor's history (app/services/badges.py), not by the model.

Placeholder wording for the hackathon demo — the Phoenix Bikes team must verify every
statement before real use.
"""

IMPACT_OPTIONS: list[dict[str, str]] = [
    {
        "key": "earn_a_bike",
        "text": "It helps a young rider in our Earn-A-Bike program build a bike of their own "
        "and the skills to keep it rolling.",
    },
    {
        "key": "repair_skills",
        "text": "It keeps tools and parts on the bench so teens can learn real repair skills "
        "after school.",
    },
    {
        "key": "refurbished_bikes",
        "text": "It helps us refurbish donated bikes and get them back on the road with new "
        "riders.",
    },
    {
        "key": "safe_riding",
        "text": "It supports safe-riding classes and helmets for kids riding to school.",
    },
    {
        "key": "shop_open",
        "text": "It keeps our community shop open and welcoming to anyone who walks in with a "
        "flat tire.",
    },
    {
        "key": "youth_mentors",
        "text": "It gives a teen mechanic paid hours mentoring younger riders in the shop.",
    },
]

# One badge per note, computed from giving history by app/services/badges.py.
BADGES: list[dict[str, str]] = [
    {
        "key": "lantern",
        "title": "Lantern",
        "meaning": "Given in memory or in honor of someone: a light carried forward.",
    },
    {
        "key": "spoke_star",
        "title": "Spoke Star",
        "meaning": "Every spoke matters. Your support helps the whole wheel stay true.",
    },
    {
        "key": "chain_keeper",
        "title": "Chain Keeper",
        "meaning": "You keep things moving: a steady link between young riders and the road.",
    },
    {
        "key": "first_gear",
        "title": "First Gear",
        "meaning": "Your very first gift to Phoenix Bikes. Every journey starts in first gear.",
    },
    {
        "key": "headlight",
        "title": "Headlight",
        "meaning": "You came back and lit the way again for the next rider.",
    },
    {
        "key": "tailwind",
        "title": "Tailwind",
        "meaning": "You showed up exactly when it helped most, like a tailwind on a long climb.",
    },
    {
        "key": "kickstand",
        "title": "Kickstand",
        "meaning": "Quiet, dependable support that holds everything upright.",
    },
]

IMPACT_BY_KEY = {o["key"]: o for o in IMPACT_OPTIONS}
BADGE_BY_KEY = {b["key"]: b for b in BADGES}
