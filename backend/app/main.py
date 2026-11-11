import asyncio
import contextlib
import html
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import SessionLocal, init_db
from .models import Floor
from .rooms import dust_sweep
from .routes import admin, community, floors
from .rules import is_basement, label, parse_label, special
from .seed import seed

log = logging.getLogger("elevator")


async def _sweeper() -> None:
    while True:
        try:
            with SessionLocal() as db:
                result = dust_sweep(db)
                if any(result.values()):
                    log.info("dust sweep: %s", result)
        except Exception:  # keep the loop alive
            log.exception("dust sweep failed")
        await asyncio.sleep(settings.dust_sweep_minutes * 60)


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.seed_on_start:
        with SessionLocal() as db:
            seed(db)
    task = asyncio.create_task(_sweeper()) if settings.dust_sweep_minutes > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="The Internet Elevator", lifespan=lifespan)
if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"],
                       allow_headers=["*"])

app.include_router(floors.router)
app.include_router(community.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"ok": True}


# ------------------------------------------------------------------ frontend + previews

DIST = settings.frontend_dist
INDEX = DIST / "index.html"
if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

DEFAULT_TITLE = "The Internet Elevator"
DEFAULT_DESC = "One building. 10,000 floors. Every floor belongs to a stranger."


def _base_url(request: Request) -> str:
    return settings.public_url or str(request.base_url).rstrip("/")


def _meta_for(n: int | None) -> tuple[str, str, str]:
    """(title, description, preview path) for a floor."""
    if n is None:
        return DEFAULT_TITLE, DEFAULT_DESC, "/api/floors/0/preview.png"
    title, desc = f"Floor {label(n)} · {DEFAULT_TITLE}", DEFAULT_DESC
    sp = special(n)
    if sp == "lobby":
        title = DEFAULT_TITLE
    elif sp == "brick":
        title, desc = f"Floor 404 · {DEFAULT_TITLE}", "Floor not found."
    elif sp == "roof":
        title, desc = f"The Roof · {DEFAULT_TITLE}", "Floor 10,000. Nothing above but stars."
    elif sp is None:
        with SessionLocal() as db:
            f = db.get(Floor, n)
            if f is None:
                desc = f"Floor {label(n)} is for rent. Claim it."
            elif f.status in ("live", "dusty"):
                if is_basement(n):
                    title = f"Basement {label(n)} · {DEFAULT_TITLE}"
                    desc = f.message[:200]
                else:
                    title = f"{f.name} · Floor {label(n)}"
                    desc = f.message[:200] or DEFAULT_DESC
    return title, desc, f"/api/floors/{n}/preview.png"


def _page(request: Request, n: int | None, path: str) -> HTMLResponse:
    title, desc, img = _meta_for(n)
    base = _base_url(request)
    tags = "\n".join([
        f'<meta property="og:title" content="{html.escape(title)}">',
        f'<meta property="og:description" content="{html.escape(desc)}">',
        f'<meta property="og:image" content="{base}{img}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:url" content="{base}{html.escape(path)}">',
        '<meta property="og:type" content="website">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="description" content="{html.escape(desc)}">',
    ])
    if INDEX.exists():
        doc = INDEX.read_text(encoding="utf-8")
        doc = doc.replace(f"<title>{DEFAULT_TITLE}</title>", f"<title>{html.escape(title)}</title>")
        doc = doc.replace("<!--og-->", tags)
    else:
        doc = (f"<!doctype html><html><head><title>{html.escape(title)}</title>{tags}</head>"
               "<body>Frontend not built. Run <code>npm run build</code> in frontend/.</body></html>")
    return HTMLResponse(doc)


@app.get("/floor/{label_}", include_in_schema=False)
@app.get("/floor/{label_}/edit", include_in_schema=False)
def floor_page(label_: str, request: Request):
    n = parse_label(label_)
    return _page(request, n, request.url.path)


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str, request: Request):
    if path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    file = (DIST / path).resolve()
    if path and file.is_file() and DIST.resolve() in file.parents:
        return FileResponse(file)
    return _page(request, None, "/" + path)
