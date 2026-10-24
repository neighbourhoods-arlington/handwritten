from datetime import date
from decimal import Decimal

import pytest

ALL_TOOLS = {
    "list_documents", "get_document", "create_document", "search_documents",
    "search_donors", "get_donor", "update_donor_address",
    "get_donor_summary", "list_donor_summaries",
    "list_gifts", "find_eligible_gifts",
    "list_notes", "get_note", "create_note_draft", "update_note_draft",
    "reject_note", "approve_note", "mark_note_sent",
    "list_import_batches", "import_gifts_csv",
}  # fmt: skip
STAFF_TOOLS = {"approve_note", "mark_note_sent", "import_gifts_csv"}


async def test_all_tools_registered():
    from app.services.mcp_client import make_mcp_client

    async with make_mcp_client() as client:
        names = {t.name for t in await client.list_tools()}
    assert names == ALL_TOOLS


async def test_agent_does_not_see_staff_tools():
    from app.services.mcp_client import agent_visible_tools, make_mcp_client

    async with make_mcp_client() as client:
        visible = {t.name for t in agent_visible_tools(await client.list_tools())}
    assert visible == ALL_TOOLS - STAFF_TOOLS


def test_normalize_header():
    from app.mcp.tools.imports import normalize_header

    assert normalize_header("Account Number") == "account_number"
    assert normalize_header(" Gift-Date ") == "gift_date"


def test_parse_amount():
    from app.mcp.tools.imports import parse_amount

    assert parse_amount("$1,234.5") == Decimal("1234.50")
    with pytest.raises(ValueError):
        parse_amount("0")
    with pytest.raises(ValueError):
        parse_amount("abc")


def test_parse_date():
    from app.mcp.tools.imports import parse_date

    assert parse_date("2026-10-21") == date(2026, 10, 21)
    assert parse_date("10/21/2026") == date(2026, 10, 21)
    with pytest.raises(ValueError):
        parse_date("21.10.2026")


def test_source_hash_is_stable_and_prefers_transaction_number():
    from app.mcp.tools.imports import gift_source_hash

    row = {"account_number": "A1", "fund": "General"}
    d, amt = date(2026, 10, 21), Decimal("25.00")
    assert gift_source_hash(row, d, amt) == gift_source_hash(dict(row), d, amt)
    assert gift_source_hash(row, d, amt) != gift_source_hash(row, d, Decimal("26.00"))
    with_txn = row | {"transaction_number": "T9"}
    assert gift_source_hash(with_txn, d, amt) == gift_source_hash(
        {"account_number": "other", "transaction_number": "T9"}, date(2020, 1, 1), amt
    )


def test_week_monday():
    from app.mcp.tools.notes import week_monday

    assert week_monday(date(2026, 10, 24)) == date(2026, 10, 19)  # Saturday → Monday
    assert week_monday(date(2026, 10, 19)) == date(2026, 10, 19)
