"""thank_you_notes: share token, badge, impact option, model and checks

Keep in sync with datasets/schemas/01_schema.sql.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-24 18:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("thank_you_notes", sa.Column("share_token", sa.Text(), nullable=True))
    op.add_column("thank_you_notes", sa.Column("badge_key", sa.Text(), nullable=True))
    op.add_column("thank_you_notes", sa.Column("impact_key", sa.Text(), nullable=True))
    op.add_column("thank_you_notes", sa.Column("llm_model", sa.Text(), nullable=True))
    op.add_column(
        "thank_you_notes",
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_unique_constraint(
        "thank_you_notes_share_token_key", "thank_you_notes", ["share_token"]
    )


def downgrade() -> None:
    op.drop_constraint("thank_you_notes_share_token_key", "thank_you_notes", type_="unique")
    for col in ("checks", "llm_model", "impact_key", "badge_key", "share_token"):
        op.drop_column("thank_you_notes", col)
