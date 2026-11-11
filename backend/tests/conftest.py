import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp / 'test.db'}"
os.environ["ADMIN_TOKEN"] = "admin-secret"
os.environ["SEED_ON_START"] = "false"
os.environ["DUST_SWEEP_MINUTES"] = "0"
os.environ["DICE_POOL_DELAY_MINUTES"] = "0"
os.environ["REDIS_URL"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.ratelimit import limiter  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    limiter.reset()
    with TestClient(app) as c:
        yield c


def dev(i: int = 1) -> dict:
    return {"X-Device-Id": f"device-{i:04d}-test"}
