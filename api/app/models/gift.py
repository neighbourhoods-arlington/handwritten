from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Computed, Date, ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# "Raise + Ride" campaign gifts count as raise_ride, everything else as direct.
# If the real Bloomerang campaign name differs, change only this expression.
CHANNEL_EXPR = "CASE WHEN lower(campaign) LIKE 'raise + ride%' THEN 'raise_ride' ELSE 'direct' END"


class Gift(Base):
    """A single gift (donation) made by a donor."""

    __tablename__ = "gifts"
    __table_args__ = (
        CheckConstraint("amount > 0", name="gifts_amount_check"),
        Index("gifts_donor_idx", "donor_id"),
        Index("gifts_date_idx", "gift_date"),
    )

    gift_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    donor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("donors.donor_id", ondelete="CASCADE"), nullable=False
    )
    gift_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fund: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign: Mapped[str | None] = mapped_column(Text, nullable=True)
    appeal: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Donor's note / memorial-honor note, etc.
    receipt_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(Text, Computed(CHANNEL_EXPR, persisted=True))
    # Re-importing the same export must not insert the same gift twice
    source_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    batch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("import_batches.batch_id"), nullable=True
    )

    donor: Mapped["Donor"] = relationship(back_populates="gifts")  # noqa: F821
    batch: Mapped["ImportBatch | None"] = relationship(back_populates="gifts")  # noqa: F821
    notes: Mapped[list["ThankYouNote"]] = relationship(back_populates="gift")  # noqa: F821
