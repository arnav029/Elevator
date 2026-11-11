"""Renders a floor to a 1200x630 PNG for Open Graph previews."""
import io
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .constants import GRID, PALETTE, WALLPAPERS
from .rules import label, window_view

W, H = 1200, 630
_WINDOW_SKY = {
    "street": ("#8fc6e8", "#d7ecf7"),
    "skyline": ("#5fa3d9", "#c4e2f5"),
    "clouds": ("#9cc4e4", "#ffffff"),
    "thin": ("#0c1240", "#3b4a8f"),
    "stars": ("#02030a", "#101530"),
}


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


@lru_cache(maxsize=8)
def _font(size: int) -> ImageFont.ImageFont:
    for name in ("DejaVuSansMono-Bold.ttf", "consolab.ttf", "courbd.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int, max_lines: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and " ".join(lines) != " ".join(words):
        lines[-1] = lines[-1].rstrip(".") + "..."
    return lines


def _gradient(img: Image.Image, box, top: str, bottom: str) -> None:
    x0, y0, x1, y1 = box
    t, b = _rgb(top), _rgb(bottom)
    d = ImageDraw.Draw(img)
    for y in range(y0, y1):
        k = (y - y0) / max(1, y1 - y0 - 1)
        d.line([(x0, y), (x1 - 1, y)], fill=tuple(round(t[i] + (b[i] - t[i]) * k) for i in range(3)))


def _footer(d: ImageDraw.ImageDraw, color="#f4f4f4") -> None:
    d.text((60, H - 70), "THE INTERNET ELEVATOR  ·  10,000 floors, every one owned by a stranger",
           font=_font(24), fill=color)


def render_room(number: int, name: str, pixels: str, wallpaper: int) -> bytes:
    wall = WALLPAPERS[wallpaper % len(WALLPAPERS)]["color"]
    img = Image.new("RGB", (W, H), _rgb(wall))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 110, W, H], fill="#5b3a29")  # floorboards
    for x in range(0, W, 120):
        d.line([(x, H - 110), (x, H)], fill="#4a2f21", width=3)

    view = window_view(number) or "clouds"
    top, bottom = _WINDOW_SKY[view]
    _gradient(img, (60, 60, 300, 300), top, bottom)
    d.rectangle([60, 60, 300, 300], outline="#f4f4f4", width=10)
    d.line([(180, 60), (180, 300)], fill="#f4f4f4", width=8)
    d.line([(60, 180), (300, 180)], fill="#f4f4f4", width=8)

    # Wall art, 10x scale, in a frame.
    art = Image.new("RGB", (GRID, GRID))
    art.putdata([_rgb(PALETTE[int(ch, 16)]) for ch in pixels])
    art = art.resize((GRID * 11, GRID * 11), Image.NEAREST)
    ax, ay = 360, 50
    d.rectangle([ax - 18, ay - 18, ax + art.width + 18, ay + art.height + 18], fill="#2b1d14")
    img.paste(art, (ax, ay))

    tx = ax + art.width + 60
    dark = sum(_rgb(wall)) < 330
    ink = "#f4f4f4" if dark else "#1a1c2c"
    d.text((tx, 70), f"FLOOR {label(number)}", font=_font(56), fill=ink)
    for i, line in enumerate(_wrap(d, name or "Untitled room", _font(40), W - tx - 50, 4)):
        d.text((tx, 160 + i * 52), line, font=_font(40), fill=ink)
    _footer(d)
    return _png(img)


def render_basement(number: int, message: str) -> bytes:
    img = Image.new("RGB", (W, H), "#121212")
    d = ImageDraw.Draw(img)
    d.ellipse([W // 2 - 300, -200, W // 2 + 300, 350], fill="#2a2618")
    d.line([(W // 2, 0), (W // 2, 70)], fill="#555", width=4)
    d.ellipse([W // 2 - 22, 70, W // 2 + 22, 120], fill="#ffcd75")
    d.text((60, 150), f"BASEMENT {label(number)}", font=_font(48), fill="#94b0c2")
    for i, line in enumerate(_wrap(d, message, _font(34), W - 120, 6)):
        d.text((60, 230 + i * 46), line, font=_font(34), fill="#d8d0b8")
    _footer(d, "#777")
    return _png(img)


@lru_cache(maxsize=256)
def render_static(kind: str, number: int) -> bytes:
    """Previews for empty floors, the lobby and special floors (not stored)."""
    img = Image.new("RGB", (W, H), "#8d8d8a")
    d = ImageDraw.Draw(img)
    if kind == "lobby":
        img.paste("#3a2e2a", (0, 0, W, H))
        d.text((60, 200), "THE LOBBY", font=_font(80), fill="#ffcd75")
        d.text((60, 310), "Press a floor. Any floor.", font=_font(40), fill="#f4f4f4")
    elif kind == "brick":
        img.paste("#8e3b2e", (0, 0, W, H))
        for row, y in enumerate(range(0, H, 50)):
            d.line([(0, y), (W, y)], fill="#d9c8b4", width=4)
            for x in range(-100 if row % 2 else -50, W, 100):
                d.line([(x, y), (x, y + 50)], fill="#d9c8b4", width=4)
        d.text((300, 250), "404: FLOOR NOT FOUND", font=_font(56), fill="#f4f4f4")
    elif kind == "roof":
        img.paste("#02030a", (0, 0, W, H))
        import random
        rng = random.Random(10000)
        for _ in range(300):
            x, y = rng.randrange(W), rng.randrange(H)
            d.point((x, y), fill="#f4f4f4")
        d.text((60, 250), "THE ROOF · FLOOR 10,000", font=_font(64), fill="#f4f4f4")
    else:  # empty
        d.rectangle([W // 2 - 220, 170, W // 2 + 220, 380], fill="#f4f4f4", outline="#b13e53", width=10)
        d.text((W // 2 - 170, 200), "FOR RENT", font=_font(80), fill="#b13e53")
        d.text((W // 2 - 170, 310), f"Floor {label(number)}", font=_font(40), fill="#1a1c2c")
    _footer(d)
    return _png(img)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
