"""Room validation, dice-pool gate, serialisation and the dust sweep."""
import re
from collections import Counter
from datetime import datetime, timedelta

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from . import preview
from .config import settings
from .constants import COBWEB_DAYS, LIMITS, OBJECTS, PIXEL_COUNT, RECLAIM_DAYS, WALLPAPERS, BLANK_PIXELS
from .db import utcnow
from .models import Floor, Note, Report
from .moderation import clean
from .rules import is_basement

_PIXELS_RE = re.compile(rf"^[0-9a-f]{{{PIXEL_COUNT}}}$")


class RoomIn(BaseModel):
    name: str = Field(default="", max_length=200)
    message: str = Field(default="", max_length=1000)
    pixels: str = Field(default=BLANK_PIXELS, max_length=PIXEL_COUNT + 10)
    wallpaper: int = 0
    objects: list[int] = Field(default_factory=list, max_length=10)


def apply_room(floor: Floor, data: RoomIn) -> None:
    """Validate input and copy it onto the floor. Basements only keep anonymous text."""
    if is_basement(floor.number):
        floor.name = ""
        floor.message = clean(data.message, "message", LIMITS["message"], required=True, multiline=True)
        floor.pixels = BLANK_PIXELS
        floor.wallpaper = 0
        floor.objects = []
        return
    pixels = (data.pixels or "").lower()
    if not _PIXELS_RE.match(pixels):
        raise HTTPException(422, "Wall art must be 32x32 pixels from the 16-colour palette.")
    if not 0 <= data.wallpaper < len(WALLPAPERS):
        raise HTTPException(422, "Unknown wallpaper.")
    objects = list(dict.fromkeys(data.objects))
    if len(objects) > LIMITS["objects"] or any(not 0 <= o < len(OBJECTS) for o in objects):
        raise HTTPException(422, f"Pick up to {LIMITS['objects']} objects from the list.")
    floor.name = clean(data.name, "room name", LIMITS["name"], required=True)
    floor.message = clean(data.message, "message", LIMITS["message"], multiline=True)
    floor.pixels = pixels
    floor.wallpaper = data.wallpaper
    floor.objects = objects


def passes_pool_check(floor: Floor) -> bool:
    """Automated gate for the dice pool: the room must look like someone made it."""
    if is_basement(floor.number):
        return len(floor.message.strip()) >= 10
    if not floor.name.strip():
        return False
    counts = Counter(floor.pixels)
    drawn = PIXEL_COUNT - counts.most_common(1)[0][1]
    return drawn >= 16 and len(counts) >= 2


def gate_for_pool(floor: Floor, now: datetime | None = None) -> None:
    now = now or utcnow()
    if floor.is_staff:
        floor.pool_status, floor.pool_after = "approved", now
    elif settings.dice_pool_mode == "auto" and passes_pool_check(floor):
        floor.pool_status = "approved"
        floor.pool_after = now + timedelta(minutes=settings.dice_pool_delay_minutes)
    else:
        floor.pool_status, floor.pool_after = "pending", None


def render_preview(floor: Floor) -> None:
    if is_basement(floor.number):
        floor.preview_png = preview.render_basement(floor.number, floor.message)
    else:
        floor.preview_png = preview.render_room(floor.number, floor.name, floor.pixels, floor.wallpaper)


def room_dict(floor: Floor) -> dict:
    return {
        "name": floor.name,
        "message": floor.message,
        "pixels": floor.pixels,
        "wallpaper": floor.wallpaper,
        "objects": floor.objects or [],
        "visit_count": floor.visit_count,
        "is_staff": floor.is_staff,
        "dusty": floor.status == "dusty",
        "created_at": floor.created_at.isoformat() + "Z",
        "updated_at": floor.updated_at.isoformat() + "Z",
    }


def note_dict(note: Note, since: datetime | None = None) -> dict:
    d = {"id": note.id, "body": note.body, "created_at": note.created_at.isoformat() + "Z"}
    if since is not None:
        d["new"] = note.created_at > since
    return d


def visible_notes(db: Session, n: int) -> list[Note]:
    return list(db.scalars(
        select(Note).where(Note.floor_number == n, Note.status == "visible")
        .order_by(Note.created_at.desc(), Note.id.desc()).limit(LIMITS["notesShown"])
    ))


def remove_floor(db: Session, floor: Floor) -> None:
    """Put a floor back on the market, with its notes and reports."""
    note_ids = list(db.scalars(select(Note.id).where(Note.floor_number == floor.number)))
    if note_ids:
        db.execute(delete(Report).where(Report.target_type == "note", Report.target_id.in_(note_ids)))
    db.execute(delete(Note).where(Note.floor_number == floor.number))
    db.execute(delete(Report).where(Report.target_type == "floor", Report.target_id == floor.number))
    db.delete(floor)


def dust_sweep(db: Session, now: datetime | None = None) -> dict:
    """Cobwebs after 30 quiet days; back on the market after 90 with no owner return."""
    now = now or utcnow()
    cobweb_cutoff = now - timedelta(days=COBWEB_DAYS)
    reclaim_cutoff = now - timedelta(days=RECLAIM_DAYS)
    dusted = db.execute(
        update(Floor)
        .where(Floor.status == "live", Floor.is_staff.is_(False), Floor.last_visited_at < cobweb_cutoff)
        .values(status="dusty")
    ).rowcount
    stale = list(db.scalars(select(Floor).where(
        Floor.is_staff.is_(False),
        Floor.status != "hidden",
        Floor.last_visited_at < reclaim_cutoff,
        Floor.owner_seen_at < reclaim_cutoff,
    )))
    for floor in stale:
        remove_floor(db, floor)
    db.commit()
    return {"dusted": dusted, "reclaimed": len(stale)}
