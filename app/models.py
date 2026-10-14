from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CurvePeriod(Base):
    __tablename__ = "curve_periods"
    __table_args__ = (UniqueConstraint("sheet_key", "sequence", name="uq_curve_sheet_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sheet_key: Mapped[str] = mapped_column(String(80), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    period_date: Mapped[date] = mapped_column(Date)
    planned_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    actual_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    project_area: Mapped[str] = mapped_column(String(200), index=True)
    drawing: Mapped[str] = mapped_column(String(200), default="")
    item_code: Mapped[str] = mapped_column(String(120), default="")
    name: Mapped[str] = mapped_column(String(400))
    starts_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_on: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    manufactured_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    shipped_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    source_row: Mapped[int] = mapped_column(Integer, default=0)
    database_row: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AreaSummary(Base):
    __tablename__ = "area_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_area: Mapped[str] = mapped_column(String(200), unique=True)
    task_count: Mapped[int] = mapped_column(Integer)
    planned_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    manufactured_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3))
