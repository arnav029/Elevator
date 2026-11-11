"""Hand-made half floors. Only reachable when the elevator breaks down between floors.

Edit this file to add more. `at` is the floor below the half floor (7 => 7½).
"""
import random
from functools import lru_cache

from . import art


def _crawlspace() -> str:
    c = art.Canvas(0)
    c.rect(0, 22, 32, 10, 15)
    for x in range(0, 32, 6):
        c.rect(x, 0, 2, 22, 14)
    c.disk(16, 26, 3, 4).rect(15, 20, 2, 3, 14)
    c.text_center("7.5", 6, 4)
    return c.hex()


def _missing_pages() -> str:
    c = art.Canvas(13)
    rng = random.Random(4045)
    for _ in range(14):
        x, y = rng.randrange(0, 26), rng.randrange(0, 26)
        c.rect(x, y, 6, 7, 12).frame(x, y, 6, 7, 14)
        c.rect(x + 1, y + 2, 4, 1, 14).rect(x + 1, y + 4, 3, 1, 14)
    c.rect(4, 11, 24, 9, 0).text_center("404.5", 13, 11)
    return c.hex()


@lru_cache(maxsize=1)
def all_half_floors() -> dict[int, dict]:
    floors = [
        {"at": 1, "name": "Lost Property", "style": "office",
         "message": "One glove. Forty umbrellas. A birthday card addressed to 'you, probably'. "
                    "If something of yours went missing in the building, it is here, and it is not coming back.",
         "pixels": art.key().hex()},
        {"at": 7, "name": "The Crawlspace", "style": "crawl",
         "message": "The ceiling is four feet high. Someone has been living here. There is a kettle, "
                    "a reading lamp, and a library card for a library that closed in 1994.",
         "pixels": _crawlspace()},
        {"at": 12, "name": "Floor 13 (Actually)", "style": "office",
         "message": "The thirteenth floor was never removed. It was just renumbered to 12½ so nobody would notice. "
                    "Please don't tell the other floors.",
         "pixels": art.word("13", bg=1, fg=4, border=2).hex()},
        {"at": 99, "name": "The Bulb Museum", "style": "crawl",
         "message": "Every bulb that ever burned out in the basement is kept here, labelled with its last words. "
                    "Most of them said 'bzzt'.",
         "pixels": art.bulb().hex()},
        {"at": 404, "name": "Where Missing Pages Go", "style": "office",
         "message": "You found it. Every page that was ever not found ends up on this floor, filed alphabetically. "
                    "There is a desk with your name on it.",
         "pixels": _missing_pages()},
        {"at": 999, "name": "Maintenance Office", "style": "office",
         "message": "A clipboard on the wall reads: 'Elevator 1. Last inspected: never. Known faults: stops at "
                    "floors that don't exist. Status: working as intended.'",
         "pixels": art.word("OK?", bg=4, fg=0, border=0).hex()},
        {"at": 2500, "name": "The Lounge Between", "style": "lounge",
         "message": "Soft music plays from nowhere. A sign says 'For passengers whose elevator has stopped. "
                    "Please wait. Someone is always coming.'",
         "pixels": art.spiral(bg=1, fg=4).hex()},
        {"at": 5000, "name": "The Halfway Point", "style": "lounge",
         "message": "Exactly halfway up the building. A brass plaque says: 'You are halfway to something.' "
                    "It does not say what.",
         "pixels": art.word("1/2\nWAY", bg=8, fg=4, border=4).hex()},
        {"at": 7777, "name": "The Wishing Shaft", "style": "crawl",
         "message": "Coins line the floor of the shaft. People drop them from the doors on their way up. "
                    "Nobody remembers starting this.",
         "pixels": art.word("WISH", bg=0, fg=4, border=15).hex()},
        {"at": 9999, "name": "Last Stop Before the Stars", "style": "lounge",
         "message": "The air is thin and very quiet. Through a crack in the wall you can see the roof, "
                    "and above it, everything else.",
         "pixels": art.night_sky(random.Random(9999)).hex()},
        {"at": -51, "name": "The Boiler Whisper", "style": "crawl",
         "message": "The boiler down here talks if you listen. Today it said: 'warm'. Yesterday: 'warmer'. "
                    "Nobody has asked what happens next.",
         "pixels": art.noise(random.Random(51), (0, 2, 3, 15)).hex()},
    ]
    return {f["at"]: f for f in floors}


def pick(from_floor: int, to_floor: int, rng: random.Random | None = None) -> dict:
    """A half floor between the two floors if there is one, otherwise any of them."""
    rng = rng or random.Random()
    lo, hi = sorted((from_floor, to_floor))
    floors = all_half_floors()
    between = [f for at, f in floors.items() if lo <= at < hi]
    return rng.choice(between or list(floors.values()))
