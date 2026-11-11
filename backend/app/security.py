"""Owner keys, hashed identities (IP / device) and bans."""
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Ban

_DEVICE_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def new_owner_key() -> str:
    return secrets.token_urlsafe(24)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def keys_match(key: str | None, key_hash: str | None) -> bool:
    if not key or not key_hash:
        return False
    return hmac.compare_digest(hash_key(key), key_hash)


def hash_ident(value: str) -> str:
    return hmac.new(settings.secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def client_ip(request: Request) -> str:
    if settings.trust_proxy:
        fwd = request.headers.get("fly-client-ip") or request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@dataclass
class Ident:
    ip_hash: str
    device_hash: str | None

    @property
    def any_key(self) -> str:
        return self.device_hash or self.ip_hash


def get_ident(request: Request, x_device_id: str | None = Header(default=None)) -> Ident:
    device = x_device_id if x_device_id and _DEVICE_RE.match(x_device_id) else None
    return Ident(
        ip_hash=hash_ident("ip:" + client_ip(request)),
        device_hash=hash_ident("dev:" + device) if device else None,
    )


def is_banned(db: Session, ident: Ident) -> bool:
    values = [ident.ip_hash] + ([ident.device_hash] if ident.device_hash else [])
    return db.scalar(select(Ban.id).where(Ban.value_hash.in_(values)).limit(1)) is not None


def writer(ident: Ident = Depends(get_ident), db: Session = Depends(get_db)) -> Ident:
    """Dependency for any endpoint that writes user content."""
    if is_banned(db, ident):
        raise HTTPException(403, "This device has been asked to leave the building.")
    return ident


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_token:
        raise HTTPException(503, "Admin is disabled. Set ADMIN_TOKEN to enable it.")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(401, "Wrong admin token.")
