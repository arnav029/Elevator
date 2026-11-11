"""A tiny 32x32 pixel canvas plus motifs, used to furnish staff rooms and half floors.

Pixels are palette indices 0..15 stored as one hex digit each (1024 chars).
Palette: 0 ink, 1 plum, 2 red, 3 orange, 4 yellow, 5 lime, 6 green, 7 teal,
8 navy, 9 blue, 10 sky, 11 cyan, 12 white, 13 light grey, 14 grey, 15 brown.
"""
import math
import random

N = 32

# 3x5 font for short labels on walls.
FONT = {
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111",
    "3": "111001111001111", "4": "101101111001001", "5": "111100111001111",
    "6": "111100111101111", "7": "111001010010010", "8": "111101111101111",
    "9": "111101111001111", "A": "010101111101101", "B": "110101110101110",
    "C": "011100100100011", "D": "110101101101110", "E": "111100110100111",
    "F": "111100110100100", "G": "011100101101011", "H": "101101111101101",
    "I": "111010010010111", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010",
    "P": "110101110100100", "R": "110101110101101", "S": "011100010001110",
    "T": "111010010010010", "U": "101101101101111", "V": "101101101101010",
    "W": "101101111111101", "Y": "101101010010010", "?": "111001011000010",
    "!": "010010010000010", " ": "000000000000000", "-": "000000111000000",
    "+": "000010111010000", "<": "001010100010001", ">": "100010001010100",
    ".": "000000000000010", "/": "001001010100100",
}


class Canvas:
    def __init__(self, bg: int = 12) -> None:
        self.p = [[bg] * N for _ in range(N)]

    def set(self, x: int, y: int, c: int) -> "Canvas":
        if 0 <= x < N and 0 <= y < N:
            self.p[y][x] = c
        return self

    def rect(self, x: int, y: int, w: int, h: int, c: int) -> "Canvas":
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)
        return self

    def frame(self, x: int, y: int, w: int, h: int, c: int) -> "Canvas":
        for xx in range(x, x + w):
            self.set(xx, y, c)
            self.set(xx, y + h - 1, c)
        for yy in range(y, y + h):
            self.set(x, yy, c)
            self.set(x + w - 1, yy, c)
        return self

    def disk(self, cx: float, cy: float, r: float, c: int) -> "Canvas":
        for y in range(N):
            for x in range(N):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.p[y][x] = c
        return self

    def ring(self, cx: float, cy: float, r: float, c: int, t: float = 1.0) -> "Canvas":
        for y in range(N):
            for x in range(N):
                d = math.hypot(x - cx, y - cy)
                if r - t <= d <= r:
                    self.p[y][x] = c
        return self

    def line(self, x0: int, y0: int, x1: int, y1: int, c: int) -> "Canvas":
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            self.set(round(x0 + (x1 - x0) * i / steps), round(y0 + (y1 - y0) * i / steps), c)
        return self

    def tri(self, x: int, base_y: int, w: int, h: int, c: int) -> "Canvas":
        """Upward isoceles triangle with its base centred on x."""
        for i in range(h):
            half = round(w / 2 * (i + 1) / h)
            self.rect(x - half, base_y - h + 1 + i, half * 2, 1, c)
        return self

    def text(self, s: str, x: int, y: int, c: int) -> "Canvas":
        for ch in s.upper():
            glyph = FONT.get(ch, FONT["?"])
            for i, bit in enumerate(glyph):
                if bit == "1":
                    self.set(x + i % 3, y + i // 3, c)
            x += 4
        return self

    def text_center(self, s: str, y: int, c: int) -> "Canvas":
        return self.text(s, (N - (len(s) * 4 - 1)) // 2, y, c)

    def map(self, rows: list[str], x: int, y: int, legend: dict[str, int]) -> "Canvas":
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch in legend:
                    self.set(x + dx, y + dy, legend[ch])
        return self

    def hex(self) -> str:
        return "".join("0123456789abcdef"[c] for row in self.p for c in row)


# ---------------------------------------------------------------- motifs

HEART = [
    ".XX...XX.",
    "XXXX.XXXX",
    "XXXXXXXXX",
    "XXXXXXXXX",
    ".XXXXXXX.",
    "..XXXXX..",
    "...XXX...",
    "....X....",
]


def sunset(sky=3, sun=4, hills=6, ground=7) -> Canvas:
    c = Canvas(sky)
    c.rect(0, 0, N, 8, 2).rect(0, 8, N, 6, sky)
    c.disk(16, 17, 7, sun)
    c.disk(6, 30, 10, hills).disk(26, 32, 12, ground)
    return c


def night_sky(rng: random.Random, bg=8, moon=4) -> Canvas:
    c = Canvas(bg)
    for _ in range(40):
        c.set(rng.randrange(N), rng.randrange(N), rng.choice([12, 13, 4]))
    c.disk(22, 9, 5, moon).disk(24, 7, 4, bg)
    c.rect(0, 26, N, 6, 0)
    for x in range(0, N, 4):
        c.rect(x, 26 - rng.randrange(2, 9), 3, 9, 0)
    return c


def heart(bg=12, fg=2, scale=3) -> Canvas:
    c = Canvas(bg)
    ox, oy = (N - 9 * scale) // 2, (N - 8 * scale) // 2 + 1
    for y, row in enumerate(HEART):
        for x, ch in enumerate(row):
            if ch == "X":
                c.rect(ox + x * scale, oy + y * scale, scale, scale, fg)
    return c


def tree(bg=10, leaves=6, trunk=15, ground=5) -> Canvas:
    c = Canvas(bg)
    c.rect(0, 26, N, 6, ground)
    c.rect(14, 18, 4, 9, trunk)
    c.disk(16, 12, 9, leaves).disk(10, 15, 5, leaves).disk(22, 15, 5, leaves)
    c.set(12, 9, 5).set(19, 12, 5).set(15, 6, 5)
    return c


def house(bg=10, wall=2, roof=0, door=15) -> Canvas:
    c = Canvas(bg)
    c.rect(0, 27, N, 5, 6)
    c.rect(8, 16, 16, 11, wall)
    c.tri(16, 15, 22, 9, roof)
    c.rect(14, 20, 4, 7, door).rect(10, 18, 3, 3, 4).rect(19, 18, 3, 3, 4)
    c.rect(21, 7, 2, 4, 14)
    return c


def cat_face(bg=4, fur=0, eyes=5) -> Canvas:
    c = Canvas(bg)
    c.disk(16, 18, 10, fur)
    c.tri(9, 11, 8, 7, fur).tri(23, 11, 8, 7, fur)
    c.rect(11, 15, 3, 3, eyes).rect(18, 15, 3, 3, eyes)
    c.set(12, 16, 0).set(19, 16, 0)
    c.rect(15, 20, 2, 1, 2)
    c.line(6, 20, 12, 21, 12).line(6, 23, 12, 22, 12).line(20, 21, 26, 20, 12).line(20, 22, 26, 23, 12)
    return c


def waves(sky=11, sea=9, deep=8, foam=12) -> Canvas:
    c = Canvas(sky)
    c.disk(25, 6, 3, 4)
    for y in range(14, N):
        c.rect(0, y, N, 1, sea if y < 22 else deep)
    for row in (14, 19, 25):
        for x in range(N):
            if (x + row) % 8 < 3:
                c.set(x, row + (1 if (x + row) % 8 == 1 else 0), foam)
    return c


def mountains(sky=10, far=14, near=7, snow=12) -> Canvas:
    c = Canvas(sky)
    c.tri(10, 28, 26, 18, far).tri(24, 28, 22, 15, near)
    c.tri(10, 13, 6, 3, snow).tri(24, 16, 5, 3, snow)
    c.rect(0, 28, N, 4, 6)
    return c


def flower(bg=5, petal=2, center=4, stem=6) -> Canvas:
    c = Canvas(bg)
    c.rect(15, 16, 2, 14, stem)
    c.disk(11, 23, 3, stem).disk(21, 21, 3, stem)
    for a in range(0, 360, 60):
        c.disk(16 + 5 * math.cos(math.radians(a)), 11 + 5 * math.sin(math.radians(a)), 3.2, petal)
    c.disk(16, 11, 3, center)
    return c


def mushroom(bg=6, cap=2, dots=12, stem=12) -> Canvas:
    c = Canvas(bg)
    c.rect(0, 27, N, 5, 15)
    c.rect(12, 17, 8, 10, stem)
    c.disk(16, 17, 11, cap).rect(0, 17, N, 15, bg).rect(0, 27, N, 5, 15).rect(12, 17, 8, 10, stem)
    for x, y in ((10, 11), (18, 8), (22, 13), (14, 14)):
        c.disk(x, y, 1.5, dots)
    return c


def cactus(bg=4, plant=6, pot=3) -> Canvas:
    c = Canvas(bg)
    c.disk(25, 6, 3, 12)
    c.rect(13, 6, 6, 18, plant).rect(7, 11, 3, 8, plant).rect(7, 16, 6, 3, plant)
    c.rect(22, 9, 3, 7, plant).rect(19, 13, 4, 3, plant)
    c.rect(10, 24, 12, 7, pot).rect(9, 24, 14, 2, 15)
    return c


def coffee(bg=13, cup=12, liquid=15, steam=14) -> Canvas:
    c = Canvas(bg)
    c.rect(8, 14, 14, 12, cup).rect(9, 15, 12, 2, liquid)
    c.ring(23, 19, 4, cup, 2)
    c.rect(5, 26, 22, 2, cup)
    for x in (11, 15, 19):
        c.line(x, 12, x + 1, 9, steam).line(x + 1, 9, x, 6, steam)
    return c


def ghost(bg=0, body=12, eyes=0) -> Canvas:
    c = Canvas(bg)
    c.disk(16, 13, 9, body).rect(7, 13, 19, 13, body)
    for x in range(7, 26, 4):
        c.rect(x, 26, 2, 2, body)
    c.rect(12, 11, 3, 4, eyes).rect(18, 11, 3, 4, eyes)
    return c


def rainbow(bg=10) -> Canvas:
    c = Canvas(bg)
    for i, col in enumerate((2, 3, 4, 6, 9, 1)):
        c.disk(16, 28, 15 - i * 2, col)
    c.disk(16, 28, 3, bg)
    c.rect(0, 28, N, 4, 5)
    c.disk(5, 26, 4, 12).disk(27, 26, 4, 12)
    return c


def smiley(bg=9, face=4, ink=0) -> Canvas:
    c = Canvas(bg)
    c.disk(16, 16, 12, face)
    c.rect(11, 10, 3, 5, ink).rect(19, 10, 3, 5, ink)
    for x in range(9, 24):
        y = 20 + round(((x - 16) / 7) ** 2 * -3 + 3)
        c.set(x, y, ink).set(x, y + 1, ink)
    return c


def checker(a=0, b=12, size=4) -> Canvas:
    c = Canvas(a)
    for y in range(N):
        for x in range(N):
            if (x // size + y // size) % 2:
                c.p[y][x] = b
    return c


def stripes(colors=(2, 3, 4, 6, 9, 1), width=3, diagonal=True) -> Canvas:
    c = Canvas(colors[0])
    for y in range(N):
        for x in range(N):
            k = (x + y) if diagonal else x
            c.p[y][x] = colors[(k // width) % len(colors)]
    return c


def planet(rng: random.Random, bg=0, body=3, ring=13) -> Canvas:
    c = Canvas(bg)
    for _ in range(30):
        c.set(rng.randrange(N), rng.randrange(N), 12)
    c.disk(16, 16, 8, body).disk(13, 13, 2, 4)
    for x in range(2, 30):
        y = 16 + round((x - 16) * 0.3)
        if not (9 < x < 23 and y < 16):
            c.set(x, y, ring).set(x, y + 1, ring)
    return c


def word(text: str, bg=0, fg=4, border=None) -> Canvas:
    c = Canvas(bg)
    if border is not None:
        c.frame(1, 1, N - 2, N - 2, border)
    lines = text.split("\n")
    y = (N - (len(lines) * 6 - 1)) // 2
    for line in lines:
        c.text_center(line, y, fg)
        y += 6
    return c


def door(bg=14, wood=15, knob=4) -> Canvas:
    c = Canvas(bg)
    c.rect(9, 3, 14, 27, wood).frame(9, 3, 14, 27, 0)
    c.frame(11, 6, 10, 9, 0).frame(11, 17, 10, 10, 0)
    c.rect(19, 16, 2, 2, knob)
    return c


def key(bg=8, metal=4) -> Canvas:
    c = Canvas(bg)
    c.ring(10, 16, 6, metal, 3)
    c.rect(15, 15, 13, 3, metal).rect(23, 18, 2, 4, metal).rect(27, 18, 2, 3, metal)
    return c


def bulb(bg=0, glass=4, base=14) -> Canvas:
    c = Canvas(bg)
    c.line(16, 0, 16, 6, 14)
    c.rect(13, 7, 7, 4, base)
    c.disk(16, 17, 7, glass)
    c.disk(14, 15, 1.5, 12)
    return c


def fish(bg=9, body=3, water=10) -> Canvas:
    c = Canvas(bg)
    for y in range(0, N, 6):
        c.line(0, y, N, y + 1, water)
    c.disk(15, 16, 7, body)
    c.tri(26, 22, 8, 12, body)
    c.rect(23, 10, 6, 12, bg).tri(27, 22, 8, 12, body)
    c.rect(10, 14, 2, 2, 0)
    c.disk(5, 8, 1, 12).disk(8, 4, 1.4, 12)
    return c


def noise(rng: random.Random, colors=(0, 1, 8, 14)) -> Canvas:
    c = Canvas(colors[0])
    for y in range(N):
        for x in range(N):
            c.p[y][x] = rng.choice(colors)
    return c


def spiral(bg=0, fg=11) -> Canvas:
    c = Canvas(bg)
    a = 0.0
    while a < 6 * math.pi:
        r = a * 0.75
        c.set(round(16 + r * math.cos(a)), round(16 + r * math.sin(a)), fg)
        c.set(round(16 + r * math.cos(a)) + 1, round(16 + r * math.sin(a)), fg)
        a += 0.04
    return c


def city(rng: random.Random, sky=1, glow=3) -> Canvas:
    c = Canvas(sky)
    c.rect(0, 18, N, 14, glow)
    c.disk(16, 22, 6, 4)
    x = 0
    while x < N:
        w, h = rng.randrange(3, 7), rng.randrange(8, 22)
        c.rect(x, N - h, w, h, 0)
        for wy in range(N - h + 2, N - 1, 3):
            for wx in range(x + 1, x + w - 1, 2):
                if rng.random() < 0.4:
                    c.set(wx, wy, 4)
        x += w + 1
    return c
