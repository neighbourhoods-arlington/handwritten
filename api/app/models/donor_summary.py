from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DonorSummary(Base):
    """Read-only mapping of the `donor_summary` view (created in a migration)."""

    __tablename__ = "donor_summary"
    # Tells alembic autogenerate to skip this — it is a view, not a table
    __table_args__ = {"info": {"is_view": True}}

    donor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_number: Mapped[str] = mapped_column(Text)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str] = mapped_column(Text)
    gift_count: Mapped[int] = mapped_column(BigInteger)
    direct_gift_count: Mapped[int] = mapped_column(BigInteger)
    total_given: Mapped[Decimal | None] = mapped_column(Numeric)
    direct_total: Mapped[Decimal | None] = mapped_column(Numeric)
    last_gift_date: Mapped[date | None] = mapped_column(Date)
    # True when the donor has no direct gifts (Raise + Ride only)
    raise_ride_only: Mapped[bool] = mapped_column(Boolean)
    last_note_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
