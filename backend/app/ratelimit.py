"""Fixed-window rate limits. Uses Redis when REDIS_URL is set, memory otherwise."""
import threading
import time

from fastapi import HTTPException

from .config import settings
from .security import Ident

# action -> (max hits, window seconds), applied to both IP and device.
LIMITS: dict[str, tuple[int, int]] = {
    "claim": (3, 24 * 3600),
    "edit": (60, 3600),
    "note": (8, 600),
    "graffiti": (3, 600),
    "report": (20, 3600),
}


class MemoryLimiter:
    def __init__(self) -> None:
        self._data: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, window: int) -> int:
        now = time.time()
        with self._lock:
            count, expires = self._data.get(key, (0, now + window))
            if expires <= now:
                count, expires = 0, now + window
            count += 1
            self._data[key] = (count, expires)
            if len(self._data) > 100_000:  # crude cleanup
                self._data = {k: v for k, v in self._data.items() if v[1] > now}
            return count

    def reset(self) -> None:
        with self._lock:
            self._data.clear()


class RedisLimiter:
    def __init__(self, url: str) -> None:
        import redis

        self._r = redis.Redis.from_url(url)

    def hit(self, key: str, window: int) -> int:
        pipe = self._r.pipeline()
        pipe.incr(key)
        pipe.expire(key, window, nx=True)
        count, _ = pipe.execute()
        return int(count)

    def reset(self) -> None:  # pragma: no cover - only used in tests
        pass


limiter = RedisLimiter(settings.redis_url) if settings.redis_url else MemoryLimiter()


def enforce(ident: Ident, action: str) -> None:
    max_hits, window = LIMITS[action]
    keys = [f"rl:{action}:ip:{ident.ip_hash}"]
    if ident.device_hash:
        keys.append(f"rl:{action}:dev:{ident.device_hash}")
    for key in keys:
        if limiter.hit(key, window) > max_hits:
            raise HTTPException(429, "Slow down a little. Try again later.")


def first_time(key: str, window: int) -> bool:
    """True the first time `key` is seen within `window` seconds (visit de-duplication)."""
    return limiter.hit("once:" + key, window) == 1
