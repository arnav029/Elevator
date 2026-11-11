"""Building rules: which floors exist, which can be claimed, what the window shows."""
import re

from fastapi import HTTPException

from .config import settings
from .constants import MAX_FLOOR, MIN_FLOOR, SPECIAL, WINDOW_BANDS


def check_floor(n: int) -> int:
    if n < MIN_FLOOR or n > MAX_FLOOR:
        raise HTTPException(404, "The building doesn't go that far.")
    return n


def special(n: int) -> str | None:
    return SPECIAL.get(n)


def is_basement(n: int) -> bool:
    return n < 0


def is_reserved(n: int) -> bool:
    top = settings.reserved_top_floors
    return top > 0 and MAX_FLOOR - top <= n < MAX_FLOOR


def claimable(n: int) -> bool:
    return special(n) is None and not is_reserved(n)


def window_view(n: int) -> str | None:
    if n <= 0:
        return None
    for band in WINDOW_BANDS:
        if n <= band["max"]:
            return band["view"]
    return WINDOW_BANDS[-1]["view"]


def label(n: int) -> str:
    return f"B{-n}" if n < 0 else f"{n:,}"


def parse_label(s: str) -> int | None:
    s = s.strip().upper().replace(",", "")
    m = re.fullmatch(r"B(\d{1,3})", s)
    if m:
        return -int(m.group(1))
    if re.fullmatch(r"-?\d{1,5}", s):
        return int(s)
    return None


def neighbour_numbers(n: int) -> tuple[int | None, int | None]:
    """Floors directly above and below, skipping the missing 13th floor."""
    def step(x: int, d: int) -> int | None:
        x += d
        while special(x) == "missing":
            x += d
        return x if MIN_FLOOR <= x <= MAX_FLOOR else None

    return step(n, 1), step(n, -1)
