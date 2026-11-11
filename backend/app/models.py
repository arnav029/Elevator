from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, LargeBinary, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, deferred, mapped_column

from .constants import BLANK_PIXELS
from .db import Base, utcnow


class Floor(Base):
    __tablename__ = "floors"

    # -100..10000. Half floors are hand-made and live in halffloors.py.
    number: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    status: Mapped[str] = mapped_column(String(10), default="live", index=True)  # live|hidden|dusty
    name: Mapped[str] = mapped_column(String(40), default="")
    message: Mapped[str] = mapped_column(String(280), default="")
    pixels: Mapped[str] = mapped_column(String(1024), default=BLANK_PIXELS)
    wallpaper: Mapped[int] = mapped_column(SmallInteger, default=0)
    objects: Mapped[list] = mapped_column(JSON, default=list)
    owner_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    pool_status: Mapped[str] = mapped_column(String(10), default="pending", index=True)  # pending|approved
    pool_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    last_visited_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    owner_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    preview_png: Mapped[bytes | None] = deferred(mapped_column(LargeBinary, nullable=True))


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    floor_number: Mapped[int] = mapped_column(Integer, index=True)
    body: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(10), default="visible")  # visible|hidden
    device_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Graffiti(Base):
    __tablename__ = "graffiti"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    body: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(10), default="visible")
    device_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(10), index=True)  # floor|note|graffiti
    target_id: Mapped[int] = mapped_column(Integer, index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    reporter_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Ban(Base):
    __tablename__ = "bans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))  # device|ip
    value_hash: Mapped[str] = mapped_column(String(64), unique=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
