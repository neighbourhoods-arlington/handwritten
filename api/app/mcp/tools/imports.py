"""Import tools: load a Bloomerang gift export (CSV) into donors + gifts."""

import csv
import hashlib
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from fastmcp import FastMCP
from sqlalchemy import func, literal_column, select
from sqlalchemy.dialects.postgresql import insert

from app.core.db import SessionLocal
from app.mcp.tools.common import READ_ONLY, STAFF, dump
from app.models import Donor, Gift, ImportBatch
from app.schemas.gift import ImportBatchRead

imports = FastMCP("imports")

DONOR_FIELDS = ("first_name", "last_name", "email", "address_line", "city", "state", "zip")
GIFT_FIELDS = ("fund", "campaign", "appeal", "payment_method", "receipt_note")
REQUIRED_COLUMNS = {"account_number", "first_name", "last_name", "gift_date", "amount"}
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y")
MAX_REPORTED_ERRORS = 20


def normalize_header(name: str) -> str:
    """'Account Number' / 'account-number' → 'account_number'."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def parse_amount(raw: str) -> Decimal:
    try:
        amount = Decimal(raw.replace("$", "").replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"bad amount {raw!r}") from exc
    if amount <= 0:
        raise ValueError(f"amount must be > 0, got {raw!r}")
    return amount.quantize(Decimal("0.01"))


def parse_date(raw: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"bad date {raw!r} (use YYYY-MM-DD or MM/DD/YYYY)")


def gift_source_hash(row: dict[str, str | None], gift_date: date, amount: Decimal) -> str:
    """Stable id for a gift row, so re-importing the same export inserts nothing new."""
    if row.get("transaction_number"):
        key = f"txn|{row['transaction_number']}"
    else:
        parts = [row["account_number"], gift_date.isoformat(), str(amount)]
        parts += [row.get(f) or "" for f in GIFT_FIELDS]
        key = "|".join(parts)
    return hashlib.sha256(key.encode()).hexdigest()


def clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


@imports.tool(annotations=READ_ONLY)
async def list_import_batches(limit: int = 20) -> list[dict]:
    """List past imports, newest first, with row/donor/gift counts."""
    async with SessionLocal() as session:
        batches = await session.scalars(
            select(ImportBatch).order_by(ImportBatch.imported_at.desc()).limit(limit)
        )
        return [dump(ImportBatchRead, b) for b in batches]


@imports.tool(tags={STAFF})
async def import_gifts_csv(csv_content: str, source_file: str) -> dict:
    """Staff only: import a Bloomerang gift export given as CSV text.

    One row per gift. Required columns: account_number, first_name, last_name,
    gift_date, amount. Optional: email, address_line, city, state, zip, fund,
    campaign, appeal, payment_method, receipt_note, transaction_number.
    Headers are case/space-insensitive ("Account Number" works). Donors are upserted
    by account_number; gifts already imported (same source hash) are skipped.
    """
    reader = csv.DictReader(io.StringIO(csv_content.lstrip("﻿")))
    if reader.fieldnames is None:
        raise ValueError("CSV is empty")
    reader.fieldnames = [normalize_header(h) for h in reader.fieldnames]
    missing = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

    donor_rows: dict[str, dict] = {}
    gift_rows: list[dict] = []
    errors: list[str] = []
    rows_read = 0
    for line_no, raw in enumerate(reader, start=2):
        rows_read += 1
        row = {k: clean(v) for k, v in raw.items() if k}
        try:
            if not (row["account_number"] and row["first_name"] and row["last_name"]):
                raise ValueError("account_number, first_name and last_name are required")
            gift_date = parse_date(row["gift_date"] or "")
            amount = parse_amount(row["amount"] or "")
        except ValueError as exc:
            errors.append(f"line {line_no}: {exc}")
            continue
        # A donor appears once per gift; a later row only fills or overrides non-blank cells
        donor = donor_rows.setdefault(
            row["account_number"],
            {"account_number": row["account_number"], **dict.fromkeys(DONOR_FIELDS)},
        )
        donor.update({f: row[f] for f in DONOR_FIELDS if row.get(f)})
        gift_rows.append(
            {
                "account_number": row["account_number"],
                "gift_date": gift_date,
                "amount": amount,
                **{f: row.get(f) for f in GIFT_FIELDS},
                "source_hash": gift_source_hash(row, gift_date, amount),
            }
        )

    async with SessionLocal() as session:
        batch = ImportBatch(source_file=source_file, rows_read=rows_read)
        session.add(batch)
        await session.flush()

        donors_inserted = 0
        donor_ids: dict[str, int] = {}
        if donor_rows:
            stmt = insert(Donor).values(list(donor_rows.values()))
            # Newer export wins, but a blank cell never wipes out a known value
            stmt = stmt.on_conflict_do_update(
                index_elements=[Donor.account_number],
                set_={
                    **{f: func.coalesce(stmt.excluded[f], getattr(Donor, f)) for f in DONOR_FIELDS},
                    "updated_at": func.now(),
                },
            ).returning(Donor.account_number, Donor.donor_id, literal_column("xmax = 0"))
            for account_number, donor_id, inserted in await session.execute(stmt):
                donor_ids[account_number] = donor_id
                donors_inserted += int(inserted)

        gifts_inserted = 0
        if gift_rows:
            values = [
                {
                    **{k: v for k, v in g.items() if k != "account_number"},
                    "donor_id": donor_ids[g["account_number"]],
                    "batch_id": batch.batch_id,
                }
                for g in gift_rows
            ]
            result = await session.execute(
                insert(Gift)
                .values(values)
                .on_conflict_do_nothing(index_elements=[Gift.source_hash])
                .returning(Gift.gift_id)
            )
            gifts_inserted = len(result.all())

        batch.donors_inserted = donors_inserted
        batch.gifts_inserted = gifts_inserted
        await session.commit()
        await session.refresh(batch)

    return {
        "batch": dump(ImportBatchRead, batch),
        "gifts_skipped_duplicate": len(gift_rows) - gifts_inserted,
        "rows_with_errors": len(errors),
        "errors": errors[:MAX_REPORTED_ERRORS],
    }
