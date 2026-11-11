"""Minimal admin: review queue, hide, delete, approve, ban."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..db import get_db, utcnow
from ..models import Ban, Floor, Graffiti, Note, Report
from ..rooms import dust_sweep, remove_floor
from ..security import require_admin
from .community import report_target

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


def _item(kind: str, obj, reports: list[Report]) -> dict:
    d = {"type": kind, "id": obj.number if kind == "floor" else obj.id, "status": obj.status,
         "reports": [{"reason": r.reason, "at": r.created_at.isoformat() + "Z"} for r in reports],
         "created_at": obj.created_at.isoformat() + "Z"}
    if kind == "floor":
        d.update(name=obj.name, message=obj.message, pixels=obj.pixels, wallpaper=obj.wallpaper,
                 pool_status=obj.pool_status, is_staff=obj.is_staff)
    else:
        d["body"] = obj.body
        if kind == "note":
            d["floor_number"] = obj.floor_number
    return d


@router.get("/queue")
def queue(db: Session = Depends(get_db)):
    reports = list(db.scalars(select(Report).where(Report.resolved.is_(False)).order_by(Report.created_at)))
    grouped: dict[tuple[str, int], list[Report]] = {}
    for r in reports:
        grouped.setdefault((r.target_type, r.target_id), []).append(r)
    items: dict[tuple[str, int], dict] = {}
    for (kind, tid), rs in grouped.items():
        obj = report_target(db, kind, tid)
        if obj is not None:
            items[(kind, tid)] = _item(kind, obj, rs)
    for kind, model in (("floor", Floor), ("note", Note), ("graffiti", Graffiti)):
        for obj in db.scalars(select(model).where(model.status == "hidden").limit(200)):
            key = (kind, obj.number if kind == "floor" else obj.id)
            items.setdefault(key, _item(kind, obj, []))
    pending = [_item("floor", f, []) for f in db.scalars(
        select(Floor).where(Floor.pool_status == "pending", Floor.status != "hidden")
        .order_by(Floor.created_at).limit(200))]
    stats = {
        "floors": db.scalar(select(func.count()).select_from(Floor)),
        "notes": db.scalar(select(func.count()).select_from(Note)),
        "graffiti": db.scalar(select(func.count()).select_from(Graffiti)),
        "bans": db.scalar(select(func.count()).select_from(Ban)),
    }
    return {"reported": list(items.values()), "pending_pool": pending, "stats": stats}


def _resolve(db: Session, kind: str, tid: int) -> None:
    db.execute(update(Report).where(Report.target_type == kind, Report.target_id == tid).values(resolved=True))


def _get(db: Session, kind: str, tid: int):
    obj = report_target(db, kind, tid)
    if obj is None:
        raise HTTPException(404, "Not found.")
    return obj


@router.post("/{kind}/{tid}/hide")
def hide(kind: str, tid: int, db: Session = Depends(get_db)):
    _get(db, kind, tid).status = "hidden"
    _resolve(db, kind, tid)
    db.commit()
    return {"ok": True}


@router.post("/{kind}/{tid}/restore")
def restore(kind: str, tid: int, db: Session = Depends(get_db)):
    obj = _get(db, kind, tid)
    obj.status = "live" if kind == "floor" else "visible"
    _resolve(db, kind, tid)
    db.commit()
    return {"ok": True}


@router.post("/{kind}/{tid}/delete")
def delete(kind: str, tid: int, db: Session = Depends(get_db)):
    obj = _get(db, kind, tid)
    _resolve(db, kind, tid)
    if kind == "floor":
        remove_floor(db, obj)
    else:
        db.delete(obj)
    db.commit()
    return {"ok": True}


@router.post("/floor/{n}/approve")
def approve(n: int, db: Session = Depends(get_db)):
    floor = _get(db, "floor", n)
    floor.pool_status, floor.pool_after = "approved", utcnow()
    db.commit()
    return {"ok": True}


class BanIn(BaseModel):
    reason: str = ""


@router.post("/{kind}/{tid}/ban")
def ban(kind: str, tid: int, data: BanIn, db: Session = Depends(get_db)):
    """Ban the device and IP that created an item, and hide the item."""
    obj = _get(db, kind, tid)
    added = 0
    for k, value in (("device", obj.device_hash), ("ip", obj.ip_hash)):
        if value and db.scalar(select(Ban.id).where(Ban.value_hash == value)) is None:
            db.add(Ban(kind=k, value_hash=value, reason=data.reason))
            added += 1
    obj.status = "hidden"
    _resolve(db, kind, tid)
    db.commit()
    return {"ok": True, "bans_added": added}


@router.post("/sweep")
def sweep(db: Session = Depends(get_db)):
    return dust_sweep(db)
