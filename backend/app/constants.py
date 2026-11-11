"""Constants shared with the frontend (shared/constants.json)."""
import json

from .config import settings

C = json.loads(settings.shared_constants.read_text(encoding="utf-8"))

MIN_FLOOR: int = C["minFloor"]
MAX_FLOOR: int = C["maxFloor"]
PALETTE: list[str] = C["palette"]
WALLPAPERS: list[dict] = C["wallpapers"]
OBJECTS: list[str] = C["objects"]
LIMITS: dict = C["limits"]
WINDOW_BANDS: list[dict] = C["windowBands"]
SPECIAL: dict[int, str] = {int(k): v for k, v in C["special"].items()}
COBWEB_DAYS: int = C["dust"]["cobwebDays"]
RECLAIM_DAYS: int = C["dust"]["reclaimDays"]
REPORTS_TO_HIDE: int = C["reportsToHide"]
GRID: int = LIMITS["gridSize"]
PIXEL_COUNT = GRID * GRID
BLANK_PIXELS = "c" * PIXEL_COUNT  # palette index 12 = white
