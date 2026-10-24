from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

NOTE_STATUSES = ("draft", "approved", "rejected", "sent")


class ThankYouNote(Base):
    """A handwritten thank-you note drafted for a donor's gift."""

    __tablename__ = "thank_you_notes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'approved', 'rejected', 'sent')",
            name="thank_you_notes_status_check",
        ),
        # A note cannot be "approved" or "sent" without staff approval
        CheckConstraint(
            "status NOT IN ('approved', 'sent') OR approved_by IS NOT NULL",
            name="approval_required",
        ),
        # One note per gift (rejected ones excluded)
        Index(
            "one_active_note_per_gift",
            "gift_id",
            unique=True,
            postgresql_where=text("status <> 'rejected'"),
        ),
        Index("notes_donor_idx", "donor_id", "status"),
    )

    note_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    donor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("donors.donor_id", ondelete="CASCADE"), nullable=False
    )
    gift_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("gifts.gift_id", ondelete="SET NULL"), nullable=True
    )
    # Monday of the week the note belongs to
    batch_week: Mapped[date] = mapped_column(Date, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    approved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    donor: Mapped["Donor"] = relationship(back_populates="notes")  # noqa: F821
    gift: Mapped["Gift | None"] = relationship(back_populates="notes")  # noqa: F821
