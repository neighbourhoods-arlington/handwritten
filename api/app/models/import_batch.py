from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ImportBatch(Base):
    """One Bloomerang export file loaded into the database."""

    __tablename__ = "import_batches"

    batch_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    rows_read: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    donors_inserted: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    gifts_inserted: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    gifts: Mapped[list["Gift"]] = relationship(back_populates="batch")  # noqa: F821
