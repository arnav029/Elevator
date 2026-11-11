from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, undefer

from .. import halffloors, preview
from ..constants import LIMITS, MAX_FLOOR, MIN_FLOOR
from ..db import get_db, utcnow
from ..models import Floor, Note
from ..moderation import clean
from ..ratelimit import enforce, first_time
from ..rooms import (RoomIn, apply_room, gate_for_pool, note_dict, remove_floor, render_preview,
                     room_dict, visible_notes)
from ..rules import check_floor, claimable, is_basement, is_reserved, neighbour_numbers, special, window_view
from ..security import Ident, get_ident, keys_match, new_owner_key, hash_key, writer

router = APIRouter(prefix="/api")

VISIBLE = ("live", "dusty")


def in_pool_clause(now):
    return and_(Floor.status.in_(VISIBLE), Floor.pool_status == "approved",
                or_(Floor.pool_after.is_(None), Floor.pool_after <= now))


def _owned_floor(db: Session, n: int, key: str | None) -> Floor:
    floor = db.get(Floor, n)
    if floor is None or not keys_match(key, floor.owner_key_hash):
        raise HTTPException(403, "That key doesn't open this floor.")
    return floor


def _neighbour(db: Session, n: int | None) -> dict | None:
    if n is None:
        return None
    sp = special(n)
    if sp:
        return {"number": n, "special": sp}
    f = db.get(Floor, n)
    if f is None or f.status not in VISIBLE:
        return {"number": n, "empty": True}
    hint = f.name if not is_basement(n) else "someone's secret"
    return {"number": n, "name": hint}


@router.get("/floors/random")
def random_floor(exclude: int | None = None, basement: bool = False, db: Session = Depends(get_db)):
    now = utcnow()
    q = select(Floor.number).where(in_pool_clause(now))
    q = q.where(Floor.number < 0) if basement else q.where(Floor.number > 0)
    if exclude is not None:
        q = q.where(Floor.number != exclude)
    n = db.scalar(q.order_by(func.random()).limit(1))
    if n is None:
        raise HTTPException(404, "The building is empty. Claim the first floor!")
    return {"number": n}


@router.get("/floors/{n}")
def get_floor(n: int, visit: bool = False, db: Session = Depends(get_db),
              ident: Ident = Depends(get_ident), x_owner_key: str | None = Header(default=None)):
    check_floor(n)
    above, below = neighbour_numbers(n)
    base = {
        "number": n,
        "basement": is_basement(n),
        "window": window_view(n),
        "neighbours": {"above": _neighbour(db, above), "below": _neighbour(db, below)},
    }
    sp = special(n)
    if sp:
        return {**base, "kind": "special", "special": sp}
    floor = db.get(Floor, n)
    if floor is None:
        return {**base, "kind": "empty", "claimable": claimable(n), "reserved": is_reserved(n)}
    if floor.status == "hidden":
        return {**base, "kind": "hidden"}

    room = room_dict(floor)  # captured before the visit so the visitor sees the cobwebs
    # Owners don't count as visitors. Their return is recorded by /owner, which
    # also reports the notes left since their last visit.
    is_owner = keys_match(x_owner_key, floor.owner_key_hash)
    now = utcnow()
    if not is_owner and visit and first_time(f"visit:{ident.any_key}:{n}", 3600):
        floor.visit_count += 1
        floor.last_visited_at = now
        if floor.status == "dusty":
            floor.status = "live"
        db.commit()
        room["visit_count"] = floor.visit_count
    return {**base, "kind": "room", "room": room, "is_owner": is_owner,
            "notes": [note_dict(x) for x in visible_notes(db, n)]}


@router.post("/floors/{n}/claim")
def claim(n: int, data: RoomIn, db: Session = Depends(get_db), ident: Ident = Depends(writer)):
    check_floor(n)
    if not claimable(n):
        raise HTTPException(409, "This floor can't be claimed.")
    if not ident.device_hash:
        raise HTTPException(400, "Missing device id.")
    if db.get(Floor, n) is not None:
        raise HTTPException(409, "Someone already lives here.")
    if db.scalar(select(Floor.number).where(Floor.device_hash == ident.device_hash).limit(1)) is not None:
        raise HTTPException(409, "You already have a floor. One floor per person.")
    floor = Floor(number=n, status="live")
    apply_room(floor, data)
    enforce(ident, "claim")
    key = new_owner_key()
    now = utcnow()
    floor.owner_key_hash = hash_key(key)
    floor.device_hash, floor.ip_hash = ident.device_hash, ident.ip_hash
    floor.created_at = floor.updated_at = floor.last_visited_at = floor.owner_seen_at = now
    gate_for_pool(floor, now)
    render_preview(floor)
    db.add(floor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Someone just moved in. Try another floor.")
    return {"number": n, "owner_key": key, "in_pool": floor.pool_status == "approved"}


@router.put("/floors/{n}")
def edit(n: int, data: RoomIn, db: Session = Depends(get_db), ident: Ident = Depends(writer),
         x_owner_key: str | None = Header(default=None)):
    floor = _owned_floor(db, n, x_owner_key)
    enforce(ident, "edit")
    apply_room(floor, data)
    now = utcnow()
    floor.updated_at = floor.owner_seen_at = now
    gate_for_pool(floor, now)
    render_preview(floor)
    db.commit()
    return {"ok": True, "in_pool": floor.pool_status == "approved"}


@router.get("/floors/{n}/owner")
def owner_view(n: int, db: Session = Depends(get_db), x_owner_key: str | None = Header(default=None)):
    floor = _owned_floor(db, n, x_owner_key)
    since = floor.owner_seen_at
    notes = visible_notes(db, n)
    new_count = db.scalar(select(func.count()).select_from(Note).where(
        Note.floor_number == n, Note.status == "visible", Note.created_at > since))
    floor.owner_seen_at = utcnow()
    db.commit()
    return {
        "number": n,
        "room": room_dict(floor),
        "status": floor.status,
        "in_pool": floor.pool_status == "approved",
        "last_seen": since.isoformat() + "Z",
        "new_notes": new_count,
        "notes": [note_dict(x, since) for x in notes],
    }


@router.delete("/floors/{n}")
def vacate(n: int, db: Session = Depends(get_db), x_owner_key: str | None = Header(default=None)):
    floor = _owned_floor(db, n, x_owner_key)
    remove_floor(db, floor)
    db.commit()
    return {"ok": True}


class NoteIn(BaseModel):
    body: str = Field(max_length=500)


@router.post("/floors/{n}/notes")
def leave_note(n: int, data: NoteIn, db: Session = Depends(get_db), ident: Ident = Depends(writer)):
    floor = db.get(Floor, check_floor(n))
    if floor is None or floor.status not in VISIBLE:
        raise HTTPException(404, "There's nobody here to leave a note for.")
    body = clean(data.body, "note", LIMITS["note"], required=True)
    enforce(ident, "note")
    note = Note(floor_number=n, body=body, device_hash=ident.device_hash, ip_hash=ident.ip_hash)
    db.add(note)
    db.commit()
    return note_dict(note)


@router.delete("/floors/{n}/notes/{note_id}")
def delete_note(n: int, note_id: int, db: Session = Depends(get_db),
                x_owner_key: str | None = Header(default=None)):
    _owned_floor(db, n, x_owner_key)
    note = db.get(Note, note_id)
    if note is None or note.floor_number != n:
        raise HTTPException(404, "No such note.")
    db.delete(note)
    db.commit()
    return {"ok": True}


@router.get("/floors/{n}/preview.png")
def floor_preview(n: int, db: Session = Depends(get_db)):
    check_floor(n)
    sp = special(n)
    png = None
    if sp:
        png = preview.render_static(sp if sp in ("lobby", "brick", "roof") else "empty", n)
    else:
        floor = db.scalar(select(Floor).options(undefer(Floor.preview_png)).where(Floor.number == n))
        if floor is not None and floor.status in VISIBLE:
            if floor.preview_png is None:
                render_preview(floor)
                db.commit()
            png = floor.preview_png
        else:
            png = preview.render_static("empty", n)
    return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=300"})


@router.get("/half-floors/pick")
def pick_half_floor(from_: int = Query(alias="from"), to: int = Query()):
    if not (MIN_FLOOR <= from_ <= MAX_FLOOR and MIN_FLOOR <= to <= MAX_FLOOR):
        raise HTTPException(404, "Out of the shaft.")
    return halffloors.pick(from_, to)
