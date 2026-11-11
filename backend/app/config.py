"""Runtime settings, read from environment variables."""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'elevator.db'}")
    # Normalise to the psycopg (v3) driver.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _first_existing(*paths: Path) -> Path:
    for p in paths:
        if p.exists():
            return p
    return paths[0]


class Settings:
    def __init__(self) -> None:
        self.database_url = _db_url()
        self.redis_url = os.getenv("REDIS_URL", "")
        self.admin_token = os.getenv("ADMIN_TOKEN", "")
        # Pepper used when hashing IPs and device ids. Change in production.
        self.secret = os.getenv("SECRET_KEY", "dev-secret-change-me")
        # "auto": rooms enter the dice pool after an automated check and a short delay.
        # "manual": every new or edited room waits for admin approval.
        self.dice_pool_mode = os.getenv("DICE_POOL_MODE", "auto")
        self.dice_pool_delay_minutes = int(os.getenv("DICE_POOL_DELAY_MINUTES", "10"))
        # Hold back the top N floors below the roof (e.g. 100 => 9900..9999).
        self.reserved_top_floors = int(os.getenv("RESERVED_TOP_FLOORS", "0"))
        self.trust_proxy = _bool("TRUST_PROXY", False)
        self.seed_on_start = _bool("SEED_ON_START", True)
        self.dust_sweep_minutes = int(os.getenv("DUST_SWEEP_MINUTES", "60"))
        self.frontend_dist = Path(os.getenv("FRONTEND_DIST", str(REPO_DIR / "frontend" / "dist")))
        self.public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
        self.cors_origins = [o for o in os.getenv("CORS_ORIGINS", "").split(",") if o]
        self.shared_constants = Path(
            os.getenv(
                "SHARED_CONSTANTS",
                str(_first_existing(REPO_DIR / "shared" / "constants.json",
                                    BACKEND_DIR / "shared" / "constants.json")),
            )
        )


settings = Settings()
