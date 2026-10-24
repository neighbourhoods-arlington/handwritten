# CLAUDE.md — Phoenix Bikes Thank-You Notes (hackathon)

## What this project is

A tool for Phoenix Bikes' small fundraising team. Each week they export donations
from Bloomerang (CSV). This tool turns that export into **20–40 distinct, personal
thank-you notes** for **small, infrequent, direct donors**, lets staff review and
approve them, and exports approved notes in a print-ready format for a
**Uuna Tek handwriting robot**.

Hackathon context: judged on working demo, clarity of problem/solution/limitations,
and honest explanation of tool choices. No paid tool is required.
We use **fictional donor data only**.

## Hard requirements (from the official brief — do not drift from these)

1. Input is a weekly Bloomerang export (CSV). Design for the real Bloomerang
   Transactions report columns; a direct API integration is a stub only.
2. **Exclude donors who have only given through "Raise + Ride"** (the annual
   fundraising ride). A donor with both Raise + Ride and direct gifts IS eligible.
3. Each note must contain: (a) thanks for the **specific gift**, (b) a concrete
   **impact** statement, (c) the link **phoenixbikes.org/donate**.
4. Notes must be **distinct** from each other — no template with name swapped.
5. **Track past recipients** — never re-thank the same gift; respect a cooldown
   per donor.
6. **Staff approval is mandatory** before anything is exported or marked sent.
   There is no "send without review" path anywhere in the code or UI.
7. Export approved notes as print-ready text for Uuna Tek (one file per note or
   one CSV batch — see `docs/uunatek-format.md`; format is our best reading of
   the public docs, flag this as a limitation in the demo).
8. Fictional data only. Never commit anything that looks like real donor PII.

## Non-negotiable AI safety rules

- The LLM **never invents facts**. Impact statements are chosen from a curated
  `impact_options` list we maintain; amounts, dates, names come from the data row.
- LLM output is **structured JSON** (`greeting`, `gift_thanks`, `impact`,
  `closing`) validated against a schema. On validation failure: retry once,
  then mark the note `needs_attention` — never pass bad output downstream.
- Post-generation checks: donor first name present, amount matches, donate link
  present, no two notes in a batch above a similarity threshold (flag, don't
  auto-fix).
- Model is configurable via env (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`).
  Any OpenAI-compatible endpoint works: OpenRouter (default), Ollama local
  (`http://localhost:11434/v1`), etc. Never hardcode a model name.

## Data model (PostgreSQL — see `db/01_schema.sql`, `db/02_views.sql`)

- `import_batches` — one row per uploaded CSV.
- `donors` — keyed by Bloomerang `account_number` (UNIQUE).
- `gifts` — one row per transaction; `channel` is a generated column
  (`raise_ride` vs `direct`) derived from campaign/appeal/fund text.
  Dedup key: Bloomerang Transaction ID (preferred) or `source_hash`.
- `thank_you_notes` — `status ∈ {draft, approved, rejected, sent}`;
  DB CHECK enforces `approved_by IS NOT NULL` for approved/sent;
  partial unique index: one non-rejected note per gift.
- `donor_summary` view + `eligible_gifts(...)` function hold the eligibility
  logic with tunable thresholds (gift window, max amount, max lifetime direct
  gifts, cooldown days).

Known data caveats to keep in mind:
- A weekly export does NOT contain history. Either import full history once, or
  rely on Bloomerang's constituent-level columns (Lifetime Giving, Number of
  Gifts, First/Last Gift Date) stored on `donors`.
- Raise + Ride may be recorded in Campaign, Appeal, OR Fund. Match all three;
  keep the patterns in config, not hardcoded.
- Filter `transaction_type = Donation`; exclude Refunds, Pledges (unpaid),
  Soft Credits.

## Pipeline (the demo walks through exactly this)

```
CSV upload
  → parse + dedupe → donors/gifts
  → eligible_gifts() → candidate list (show WHY each was included/excluded)
  → LLM generates draft notes (structured JSON) → validation checks
  → review UI: approve / edit / regenerate / reject (staff name required)
  → approved → export file(s) for Uuna Tek → mark sent
  → past-recipient log updated
```

## Fictional test data

`data/fixtures/bloomerang_export_sample.csv` (~150–200 rows, Faker-generated)
must include deliberate edge cases so the filter logic is demonstrable:
- donor with ONLY Raise + Ride gifts → excluded
- donor with Raise + Ride AND a direct gift → included
- donor thanked last week → excluded (cooldown)
- large donor (> max amount) → excluded
- donor with no mailing address → excluded
- same gift appearing twice (re-uploaded export) → deduped

## Stack

<!-- Fill in once decided; keep this section accurate. -->
- Backend: TODO (e.g. Python/FastAPI or Go)
- DB: PostgreSQL
- Frontend: TODO (minimal review UI; server-rendered is fine)
- LLM: OpenAI-compatible client, OpenRouter by default, Ollama for offline demo
- Run everything with `docker compose up`; seed with `make seed`.

## Conventions

- Keep PRs small and the pipeline runnable end-to-end at all times; the demo
  depends on the full flow working, not on polish.
- Every eligibility decision must be explainable in the UI
  ("excluded: Raise + Ride only", "excluded: thanked 2026-10-10").
- Comments and docs in English. UI copy in English.
- No real donor data, no real API keys in the repo. `.env.example` only.
- When unsure whether something is in scope, re-read "Hard requirements".
  Prefer finishing the core loop over adding features.

## Stretch ideas (only after the core loop works end-to-end)

- QR / short link on each note → private, token-based donor page with
  AI-chosen "creative badges" (meaning-based, not count-based; no amounts
  shown; opt-in sharing; `noindex`).
- Similarity map of a batch in the review UI.
- Uuna Tek preview: line wrapping, card size, estimated write time.
- Stub `BloomerangApiSource` next to `CsvSource` to show the production path.

## Demo script (keep in sync)

1. 30s: the problem (3-person team, 30 notes/week, no time, must not repeat).
2. Upload sample CSV → show candidate list with include/exclude reasons.
3. Generate → show 3 notes side by side, point out distinctness + impact + link.
4. Review: edit one, regenerate one, approve the rest (enter staff name).
5. Export → open the Uuna Tek file.
6. Limitations slide: fictional data, no live Bloomerang connection,
   Uuna Tek format assumed from docs, LLM quality depends on chosen model.
