"""create donors, gifts, thank-you notes (datasets/schemas)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24 12:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHANNEL_EXPR = (
    "CASE WHEN lower(campaign) LIKE 'raise + ride%' THEN 'raise_ride' ELSE 'direct' END"
)

DONOR_SUMMARY_VIEW = """
CREATE VIEW donor_summary AS
SELECT
    d.donor_id,
    d.account_number,
    d.first_name,
    d.last_name,
    count(g.gift_id)                                     AS gift_count,
    count(g.gift_id) FILTER (WHERE g.channel = 'direct') AS direct_gift_count,
    sum(g.amount)                                        AS total_given,
    sum(g.amount) FILTER (WHERE g.channel = 'direct')    AS direct_total,
    max(g.gift_date)                                     AS last_gift_date,
    (count(g.gift_id) FILTER (WHERE g.channel = 'direct') = 0) AS raise_ride_only,
    (SELECT max(n.sent_at) FROM thank_you_notes n
      WHERE n.donor_id = d.donor_id AND n.status = 'sent') AS last_note_sent_at
FROM donors d
LEFT JOIN gifts g ON g.donor_id = d.donor_id
GROUP BY d.donor_id
"""

ELIGIBLE_GIFTS_FUNCTION = """
CREATE OR REPLACE FUNCTION eligible_gifts(
    p_gift_window_days    INT     DEFAULT 30,
    p_max_amount          NUMERIC DEFAULT 100,
    p_max_direct_gifts    INT     DEFAULT 3,
    p_min_days_since_note INT     DEFAULT 180,
    p_today               DATE    DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    donor_id          INT,
    gift_id           INT,
    first_name        TEXT,
    last_name         TEXT,
    gift_date         DATE,
    amount            NUMERIC,
    fund              TEXT,
    campaign          TEXT,
    appeal            TEXT,
    receipt_note      TEXT,
    direct_gift_count BIGINT
)
LANGUAGE sql STABLE AS $$
    SELECT DISTINCT ON (d.donor_id)
           d.donor_id, g.gift_id, d.first_name, d.last_name, g.gift_date, g.amount,
           g.fund, g.campaign, g.appeal, g.receipt_note, s.direct_gift_count
    FROM donors d
    JOIN gifts g          ON g.donor_id = d.donor_id AND g.channel = 'direct'
    JOIN donor_summary s  ON s.donor_id = d.donor_id
    WHERE g.gift_date BETWEEN p_today - p_gift_window_days AND p_today
      AND g.amount <= p_max_amount
      AND s.direct_gift_count <= p_max_direct_gifts
      AND coalesce(d.address_line, '') <> ''
      AND NOT EXISTS (SELECT 1 FROM thank_you_notes n WHERE n.gift_id = g.gift_id)
      AND NOT EXISTS (
            SELECT 1 FROM thank_you_notes n
             WHERE n.donor_id = d.donor_id
               AND (n.status IN ('draft', 'approved')
                    OR (n.status = 'sent'
                        AND n.sent_at::date > p_today - p_min_days_since_note)))
    ORDER BY d.donor_id, g.gift_date DESC, g.amount DESC
$$
"""


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("batch_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_file", sa.Text(), nullable=False),
        sa.Column(
            "imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("rows_read", sa.Integer(), server_default="0", nullable=False),
        sa.Column("donors_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gifts_inserted", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "donors",
        sa.Column("donor_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_number", sa.Text(), nullable=False, unique=True),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("address_line", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("zip", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "gifts",
        sa.Column("gift_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "donor_id",
            sa.Integer(),
            sa.ForeignKey("donors.donor_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("gift_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("fund", sa.Text(), nullable=True),
        sa.Column("campaign", sa.Text(), nullable=True),
        sa.Column("appeal", sa.Text(), nullable=True),
        sa.Column("payment_method", sa.Text(), nullable=True),
        sa.Column("receipt_note", sa.Text(), nullable=True),
        sa.Column("channel", sa.Text(), sa.Computed(CHANNEL_EXPR, persisted=True)),
        sa.Column("source_hash", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "batch_id", sa.Integer(), sa.ForeignKey("import_batches.batch_id"), nullable=True
        ),
        sa.CheckConstraint("amount > 0", name="gifts_amount_check"),
    )
    op.create_index("gifts_donor_idx", "gifts", ["donor_id"])
    op.create_index("gifts_date_idx", "gifts", ["gift_date"])

    op.create_table(
        "thank_you_notes",
        sa.Column("note_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "donor_id",
            sa.Integer(),
            sa.ForeignKey("donors.donor_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "gift_id",
            sa.Integer(),
            sa.ForeignKey("gifts.gift_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("batch_week", sa.Date(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("approved_by", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'rejected', 'sent')",
            name="thank_you_notes_status_check",
        ),
        sa.CheckConstraint(
            "status NOT IN ('approved', 'sent') OR approved_by IS NOT NULL",
            name="approval_required",
        ),
    )
    op.create_index(
        "one_active_note_per_gift",
        "thank_you_notes",
        ["gift_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'rejected'"),
    )
    op.create_index("notes_donor_idx", "thank_you_notes", ["donor_id", "status"])

    op.execute(DONOR_SUMMARY_VIEW)
    op.execute(ELIGIBLE_GIFTS_FUNCTION)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS eligible_gifts(INT, NUMERIC, INT, INT, DATE)")
    op.execute("DROP VIEW IF EXISTS donor_summary")
    op.drop_index("notes_donor_idx", table_name="thank_you_notes")
    op.drop_index("one_active_note_per_gift", table_name="thank_you_notes")
    op.drop_table("thank_you_notes")
    op.drop_index("gifts_date_idx", table_name="gifts")
    op.drop_index("gifts_donor_idx", table_name="gifts")
    op.drop_table("gifts")
    op.drop_table("donors")
    op.drop_table("import_batches")
