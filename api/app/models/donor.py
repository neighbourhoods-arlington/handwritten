from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Donor(Base):
    """A donor imported from Bloomerang."""

    __tablename__ = "donors"

    donor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Bloomerang account number
    account_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    zip: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    gifts: Mapped[list["Gift"]] = relationship(  # noqa: F821
        back_populates="donor", cascade="all, delete-orphan", passive_deletes=True
    )
    notes: Mapped[list["ThankYouNote"]] = relationship(  # noqa: F821
        back_populates="donor", cascade="all, delete-orphan", passive_deletes=True
    )
