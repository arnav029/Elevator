"""Lobby, elevator graffiti and reports."""
import hashlib
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import LIMITS, REPORTS_TO_HIDE
from ..db import get_db, utcnow
from ..models import Floor, Graffiti, Note, Report
from ..moderation import clean
from ..ratelimit import enforce
from ..rules import MAX_FLOOR, MIN_FLOOR, SPECIAL, is_reserved
from ..security import Ident, writer
from .floors import VISIBLE, in_pool_clause

router = APIRouter(prefix="/api")


def _brief(f: Floor) -> dict:
    return {"number": f.number, "name": f.name or "a secret", "visit_count": f.visit_count,
            "is_staff": f.is_staff}


@router.get("/lobby")
def lobby(db: Session = Depends(get_db)):
    now = utcnow()
    pool = select(Floor).where(in_pool_clause(now), Floor.number > 0)
    newest = list(db.scalars(pool.order_by(Floor.created_at.desc()).limit(8)))
    popular = list(db.scalars(pool.order_by(Floor.visit_count.desc()).limit(8)))
    numbers = list(db.scalars(select(Floor.number).where(in_pool_clause(now), Floor.number > 0)
                              .order_by(Floor.number)))
    of_the_day = None
    if numbers:
        h = int(hashlib.sha256(date.today().isoformat().encode()).hexdigest(), 16)
        of_the_day = _brief(db.get(Floor, numbers[h % len(numbers)]))
    claimed = db.scalar(select(func.count()).select_from(Floor).where(Floor.status.in_(VISIBLE)))
    total = sum(1 for n in range(MIN_FLOOR, MAX_FLOOR + 1) if n not in SPECIAL and not is_reserved(n))
    return {
        "newest": [_brief(f) for f in newest],
        "most_visited": [_brief(f) for f in popular],
        "floor_of_the_day": of_the_day,
        "claimed": claimed,
        "total": total,
    }


@router.get("/graffiti")
def graffiti(db: Session = Depends(get_db)):
    rows = db.scalars(select(Graffiti).where(Graffiti.status == "visible")
                      .order_by(Graffiti.created_at.desc(), Graffiti.id.desc())
                      .limit(LIMITS["graffitiShown"]))
    return [{"id": g.id, "body": g.body} for g in rows]


class GraffitiIn(BaseModel):
    body: str = Field(max_length=300)


@router.post("/graffiti")
def scratch(data: GraffitiIn, db: Session = Depends(get_db), ident: Ident = Depends(writer)):
    body = clean(data.body, "line", LIMITS["graffiti"], required=True)
    enforce(ident, "graffiti")
    g = Graffiti(body=body, device_hash=ident.device_hash, ip_hash=ident.ip_hash)
    db.add(g)
    db.commit()
    return {"id": g.id, "body": g.body}


class ReportIn(BaseModel):
    target_type: str
    target_id: int
    reason: str = Field(default="", max_length=500)


def report_target(db: Session, kind: str, target_id: int):
    model = {"floor": Floor, "note": Note, "graffiti": Graffiti}.get(kind)
    if model is None:
        raise HTTPException(422, "Unknown report target.")
    return db.get(model, target_id)


@router.post("/reports")
def report(data: ReportIn, db: Session = Depends(get_db), ident: Ident = Depends(writer)):
    target = report_target(db, data.target_type, data.target_id)
    if target is None:
        raise HTTPException(404, "Nothing to report.")
    enforce(ident, "report")
    already = db.scalar(select(Report.id).where(
        Report.target_type == data.target_type, Report.target_id == data.target_id,
        Report.reporter_hash == ident.any_key, Report.resolved.is_(False)).limit(1))
    if already is None:
        db.add(Report(target_type=data.target_type, target_id=data.target_id,
                      reason=data.reason[:500], reporter_hash=ident.any_key))
        db.flush()
    open_reports = db.scalar(select(func.count(func.distinct(Report.reporter_hash))).where(
        Report.target_type == data.target_type, Report.target_id == data.target_id,
        Report.resolved.is_(False)))
    staff = isinstance(target, Floor) and target.is_staff
    if open_reports >= REPORTS_TO_HIDE and not staff:
        target.status = "hidden"
    db.commit()
    return {"ok": True}
