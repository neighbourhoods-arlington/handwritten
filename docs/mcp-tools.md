# MCP tools reference

The Handwritten MCP server (`handwritten-mcp`) exposes **20 tools**, **2 prompts** and **1 resource**.
It helps Phoenix Bikes staff send handwritten thank-you notes to small, infrequent donors:
find eligible gifts, look up donors, draft notes, get them approved by staff, and record
when they are mailed.

- Code: [`api/app/mcp/server.py`](../api/app/mcp/server.py), tools in [`api/app/mcp/tools/`](../api/app/mcp/tools/)
- Data schema: [`datasets/schemas/`](../datasets/schemas/) → migration [`0002`](../api/alembic/versions/20261024_1200_0002_create_donor_notes.py)

## Contents

- [Connecting](#connecting)
- [Workflow](#workflow)
- [Who can call what](#who-can-call-what)
- [Tool index](#tool-index)
- [Donors](#donors) · [Gifts](#gifts) · [Notes](#notes) · [Imports](#imports) · [Documents](#documents)
- [Prompts and resources](#prompts-and-resources)
- [Errors](#errors)
- [Adding a tool](#adding-a-tool)

## Connecting

| Method | Address / command |
|--------|-------------------|
| HTTP (with the API running) | `http://localhost:8000/mcp` |
| Claude Code | `claude mcp add --transport http handwritten http://localhost:8000/mcp` |
| stdio (Claude Desktop, etc.) | `make mcp-stdio` → `python -m app.mcp.server` |
| Ollama agent | `POST /api/v1/agent/chat` — connects to the server in-process |

## Workflow

```
 Bloomerang CSV
      │  import_gifts_csv                      (staff)
      ▼
 donors + gifts ──────────────┐
      │                       │ search_donors / get_donor / list_gifts / list_donor_summaries
      │  find_eligible_gifts  │
      ▼                       │
 this week's candidates       │
      │  create_note_draft    (agent writes)
      ▼
   draft ──update_note_draft──▶ draft
      │  \
      │   reject_note ──▶ rejected   (the gift can get a new draft)
      │  approve_note                          (staff)
      ▼
  approved ──reject_note──▶ rejected
      │  mark_note_sent                        (staff)
      ▼
    sent
```

A note only moves along the arrows above. Any other transition returns an error.

## Who can call what

The 3 tools tagged `staff` are **hidden from the Ollama agent** (they do not appear in
`/api/v1/agent/tools`), and the agent refuses them even if the model guesses the name.
The database's `approval_required` rule requires a person to sign off on every note.
Claude Code and other MCP clients see all 20 tools.

| Tag | Tools | Ollama agent | Claude / others |
|-----|-------|:---:|:---:|
| — | the other 17 | ✅ | ✅ |
| `staff` | `approve_note`, `mark_note_sent`, `import_gifts_csv` | ❌ | ✅ |

Read-only tools carry the `readOnlyHint: true` annotation, so clients such as Claude can call them without asking.

## Tool index

| Group | Tool | Kind | Summary |
|-------|------|------|---------|
| Donors | [`search_donors`](#search_donors) | read | Search by name, email or account number |
| | [`get_donor`](#get_donor) | read | Donor + summary + gifts + notes |
| | [`update_donor_address`](#update_donor_address) | write | Fix a mailing address |
| | [`get_donor_summary`](#get_donor_summary) | read | Giving totals for one donor |
| | [`list_donor_summaries`](#list_donor_summaries) | read | Filtered list of giving totals |
| Gifts | [`list_gifts`](#list_gifts) | read | Filtered list of gifts |
| | [`find_eligible_gifts`](#find_eligible_gifts) | read | Gifts to thank this week |
| Notes | [`list_notes`](#list_notes) | read | Filtered list of notes |
| | [`get_note`](#get_note) | read | Note + address + gift |
| | [`create_note_draft`](#create_note_draft) | write | Create a draft |
| | [`update_note_draft`](#update_note_draft) | write | Edit a draft |
| | [`reject_note`](#reject_note) | write | Reject a note |
| | [`approve_note`](#approve_note) | `staff` | Approve a note |
| | [`mark_note_sent`](#mark_note_sent) | `staff` | Record that a note was mailed |
| Imports | [`list_import_batches`](#list_import_batches) | read | Past imports |
| | [`import_gifts_csv`](#import_gifts_csv) | `staff` | Import a Bloomerang CSV |
| Documents | [`list_documents`](#documents), `get_document`, `create_document`, `search_documents` | | Handwriting transcriptions |

Money values (`amount`, `total_given`, etc.) are returned as JSON **strings** (`"25.00"`) so no precision is lost.
Dates are `YYYY-MM-DD`; timestamps are ISO 8601 in UTC.

---

## Donors

### `search_donors`

Searches by name (full name such as `"Ana Lopez"` works), email or Bloomerang account number. Case-insensitive.

| Parameter | Type | Default | |
|-----------|------|---------|--|
| `query` | string | — | required |
| `limit` | int | 10 | |

Returns: `[{donor_id, account_number, name, email, city, has_address}]`.
A donor with `has_address: false` never appears in `find_eligible_gifts`.

### `get_donor`

Everything about one donor.

| Parameter | Type | Default |
|-----------|------|---------|
| `donor_id` | int | — |
| `gift_limit` | int | 20 — number of most recent gifts |

Returns:

```json
{
  "donor":   { "donor_id": 9, "account_number": "ZZ-1", "first_name": "Ana", "address_line": "1 Main St", ... },
  "summary": { "gift_count": 2, "direct_gift_count": 2, "total_given": "65.00", "raise_ride_only": false, ... },
  "gifts":   [ { "gift_id": 11, "gift_date": "2026-10-21", "amount": "25.00", "channel": "direct", ... } ],
  "notes":   [ { "note_id": 1, "status": "sent", "body": "Thank you, Ana!", ... } ]
}
```

### `update_donor_address`

Changes only the fields given. At least one field is required.

| Parameter | Type |
|-----------|------|
| `donor_id` | int |
| `address_line`, `city`, `state`, `zip` | string, all optional |

Returns: the updated donor (`DonorRead`).

### `get_donor_summary`

One row from the `donor_summary` view: `gift_count`, `direct_gift_count`, `total_given`,
`direct_total`, `last_gift_date`, `raise_ride_only`, `last_note_sent_at`.

| Parameter | Type |
|-----------|------|
| `donor_id` | int |

### `list_donor_summaries`

Most recent giver first.

| Parameter | Type | Notes |
|-----------|------|-------|
| `raise_ride_only` | bool | `true` → donors who only gave through Raise + Ride |
| `min_direct_gifts` | int | |
| `max_direct_gifts` | int | |
| `min_total_given` | decimal | |
| `limit` | int | 50 |

---

## Gifts

**Channel**: a gift whose `campaign` starts with `Raise + Ride` is `raise_ride`; everything else is `direct`.
The database computes it (generated column). If the real campaign name differs, change
`CHANNEL_EXPR` in [`app/models/gift.py`](../api/app/models/gift.py) and in the migration.

### `list_gifts`

Newest first.

| Parameter | Type |
|-----------|------|
| `donor_id` | int |
| `channel` | `"direct"` \| `"raise_ride"` |
| `date_from`, `date_to` | date (inclusive) |
| `limit` | int, 50 |

### `find_eligible_gifts`

Calls the SQL function `eligible_gifts()`. Returns **at most one gift per donor** (the most recent).
A gift qualifies when all of these hold:

1. It is a `direct` gift (not Raise + Ride)
2. It was given in the last `gift_window_days` days
3. Amount ≤ `max_amount`
4. The donor's lifetime direct gift count ≤ `max_direct_gifts` (an "infrequent" donor)
5. The donor has a mailing address (`address_line` not blank)
6. No note was ever created for this gift (rejected ones count too)
7. The donor has no pending `draft` or `approved` note
8. The donor was not **sent** a note in the last `min_days_since_note` days

| Parameter | Type | Default |
|-----------|------|---------|
| `gift_window_days` | int | 30 |
| `max_amount` | decimal | 100 |
| `max_direct_gifts` | int | 3 |
| `min_days_since_note` | int | 180 |
| `today` | date | the database's current date |

Returns: `[{donor_id, gift_id, first_name, last_name, gift_date, amount, fund, campaign, appeal, receipt_note, direct_gift_count}]`

Pass `today` to simulate a past or future week.

---

## Notes

**Statuses**: `draft` → `approved` → `sent`, or `draft`/`approved` → `rejected`.
`batch_week` is the **Monday** of the note's week; any date you pass is moved back to its Monday.
A gift can have only **one** note that is not `rejected`.

### `list_notes`

| Parameter | Type |
|-----------|------|
| `status` | `draft` \| `approved` \| `rejected` \| `sent` |
| `batch_week` | date |
| `donor_id` | int |
| `limit` | int, 50 |

Returns: each note plus `donor_name`.

### `get_note`

| Parameter | Type |
|-----------|------|
| `note_id` | int |

Returns: `{note, donor: {name, address_line, city, state, zip}, gift}` — everything needed to address the envelope.

### `create_note_draft`

| Parameter | Type | Default |
|-----------|------|---------|
| `donor_id` | int | — |
| `body` | string | — |
| `gift_id` | int | null — a note not tied to a gift |
| `batch_week` | date | the current week |

Errors: donor not found; the gift does not belong to the donor; the gift already has an active note.

### `update_note_draft`

Only while the note is `draft`. Parameters: `note_id`, `body`.

### `reject_note`

`draft` or `approved` → `rejected`. A new draft can then be created for the gift
(but `find_eligible_gifts` will not list it again, see rule 6). Parameter: `note_id`.

### `approve_note`

`staff`. `draft` → `approved`, sets `approved_at` to now.

| Parameter | Type |
|-----------|------|
| `note_id` | int |
| `approved_by` | string — name of the approving staff member, must not be blank |

### `mark_note_sent`

`staff`. `approved` → `sent`.

| Parameter | Type | Default |
|-----------|------|---------|
| `note_id` | int | |
| `sent_at` | datetime | now |

---

## Imports

### `list_import_batches`

Past imports, newest first: `batch_id, source_file, imported_at, rows_read, donors_inserted, gifts_inserted`.
Parameter: `limit` (20).

### `import_gifts_csv`

`staff`. Takes a Bloomerang gift export as **CSV text** (not a file path).

| Parameter | Type |
|-----------|------|
| `csv_content` | string — the full CSV contents |
| `source_file` | string — file name, stored in `import_batches` |

**CSV format** — one row per gift. Header names ignore case, spaces and dashes
(`Account Number` = `account_number`). A UTF-8 BOM is fine.

| Column | Required | Notes |
|--------|:---:|-------|
| `account_number` | ✅ | Bloomerang account number |
| `first_name`, `last_name` | ✅ | |
| `gift_date` | ✅ | `YYYY-MM-DD`, `MM/DD/YYYY` or `MM/DD/YY` |
| `amount` | ✅ | `25`, `$25.00`, `1,000.00` — must be > 0 |
| `email`, `address_line`, `city`, `state`, `zip` | | |
| `fund`, `campaign`, `appeal`, `payment_method`, `receipt_note` | | |
| `transaction_number` | | If present, used for duplicate detection |

Example:

```csv
Account Number,First Name,Last Name,Address Line,City,State,Zip,Gift Date,Amount,Fund,Campaign,Receipt Note
1042,Ana,Lopez,1 Main St,Phoenix,AZ,85001,10/21/2026,$25.00,Youth Programs,Spring Appeal,In memory of Joe
1077,Cy,Kim,9 Elm,Tempe,AZ,85281,2026-10-22,40,General,Raise + Ride 2026,
```

Rules:

- **Donors** are upserted by `account_number`. A blank cell never overwrites a value already in the database.
  When a donor has several rows in the CSV, their non-blank values are merged.
- **Gifts** are protected from duplicates by `source_hash`: a SHA-256 of `transaction_number` if present,
  otherwise of account + date + amount + fund/campaign/appeal/payment_method/receipt_note.
  Re-importing the same file adds no new gifts.
- Invalid rows are skipped and the rest are imported. Everything runs in one transaction.

Returns:

```json
{
  "batch": { "batch_id": 3, "source_file": "export.csv", "rows_read": 6, "donors_inserted": 4, "gifts_inserted": 5 },
  "gifts_skipped_duplicate": 0,
  "rows_with_errors": 1,
  "errors": ["line 7: account_number, first_name and last_name are required"]
}
```

`errors` lists at most 20 rows; `rows_with_errors` is the total count.

---

## Documents

Transcriptions of handwritten documents (`documents` table).

| Tool | Parameters | Returns |
|------|------------|---------|
| `list_documents` | `limit=20` | `[{id, title, created_at}]` |
| `get_document` | `doc_id` (UUID) | `{id, title, content, source_path, created_at}` |
| `create_document` | `title`, `content=""`, `source_path=null` | `{id, title}` |
| `search_documents` | `query`, `limit=10` | `[{id, title}]` — searches title and content |

## Prompts and resources

| Name | Kind | Parameters | Purpose |
|------|------|------------|---------|
| `thank_you_note_prompt` | prompt | `first_name`, `amount`, `fund=""`, `receipt_note=""` | A 3–5 sentence thank-you note under 80 words; gently acknowledges a memorial or honoree note |
| `transcribe_prompt` | prompt | `language="English"` | Transcribe handwriting |
| `handwritten://config` | resource | — | Active configuration (no secrets) |

## Errors

A failing tool returns an MCP result with `isError: true` and a human-readable message:

| Situation | Message |
|-----------|---------|
| ID not found | `Donor 42 not found`, `Note 7 not found` |
| Wrong status | `Note 1 is 'approved'; this needs status draft` |
| Duplicate note | `Gift 11 already has an active note` |
| Gift belongs to someone else | `Gift 11 not found for donor 9` |
| Missing CSV columns | `Missing columns: amount, gift_date` |

The Ollama agent passes errors back to the model, so it can correct itself and retry.

## Adding a tool

1. Write an async function decorated with `@<domain>.tool` in the matching module (`app/mcp/tools/<domain>.py`).
   Its docstring becomes the description the model sees.
2. Add `annotations=READ_ONLY` if it only reads, or `tags={STAFF}` if it needs a person.
3. For a new domain, export it from `app/mcp/tools/__init__.py` and add it to the `mount` loop in `server.py`.
4. Update `ALL_TOOLS` in [`tests/test_mcp_tools.py`](../api/tests/test_mcp_tools.py) and add it to this document.
