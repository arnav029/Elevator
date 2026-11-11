"""Text filter: profanity, slurs, links. Runs on every piece of text before saving.

This is a first line of defence, not a complete one. Extend the word lists as
reports come in; reports and the admin queue catch the rest.
"""
import re
import unicodedata

from fastapi import HTTPException

# Matched against whole words (after leetspeak normalisation and squashing repeats).
_WORDS = {
    "fuck", "fucker", "fucking", "fucked", "fuk", "fck", "motherfucker", "shit", "shitty",
    "bullshit", "cunt", "bitch", "bitches", "asshole", "arsehole", "dick", "dickhead", "cock",
    "pussy", "whore", "slut", "bastard", "wank", "wanker", "twat", "prick", "porn", "porno",
    "rape", "raped", "rapist", "nazi", "heil", "kys", "retard", "retarded", "spic", "chink",
    "kike", "coon", "gook", "dyke", "tranny", "fag", "fags", "cum", "jizz", "nude", "nudes",
    "sex", "sexy", "hentai", "onlyfans",
}
# Matched as substrings of the letters-only text, to catch "f a g g o t" style spacing.
# Only long, unambiguous strings belong here.
_SUBSTRINGS = (
    "nigger", "nigga", "faggot", "wetback", "raghead", "towelhead", "beaner",
    "killyourself", "motherfuck",
)
_PHRASES = (
    re.compile(r"\bkill\s+(your|ur)\s*self\b"),
    re.compile(r"\bgo\s+die\b"),
)

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
                       "@": "a", "$": "s", "!": "i", "|": "l", "+": "t"})

_LINK = re.compile(
    r"(https?:|www\.|://|\b[a-z0-9-]+\s*(\.|\(dot\)|\[dot\]|\sdot\s)\s*"
    r"(com|net|org|io|co|gg|xyz|ly|me|tv|app|dev|info|biz|ru|uk|de|link|site|online|club|top|sh|to)\b"
    r"|\S+@\S+\.\S+)",
    re.IGNORECASE,
)
_CONTROL = re.compile(r"[\u0000-\u0008\u000b-\u001f\u007f​-‏‪-‮⁦-⁩]")


def _normalise(text: str) -> str:
    t = unicodedata.normalize("NFKD", text)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return t.lower().translate(_LEET)


def _squash(word: str) -> str:
    return re.sub(r"(.)\1+", r"\1", word)


_SQUASHED_WORDS = {_squash(w) for w in _WORDS}


def problem(text: str) -> str | None:
    """Return a reason string if the text is not allowed, else None."""
    if _LINK.search(text):
        return "Links aren't allowed in the building."
    norm = _normalise(text)
    tokens = re.findall(r"[a-z]+", norm)
    # Re-join spaced-out spellings: "f.u.c.k" / "f u c k" -> "fuck".
    joined, run = [], []
    for t in tokens + [""]:
        if len(t) == 1:
            run.append(t)
            continue
        if len(run) >= 3:
            joined.append("".join(run))
        run = []
    for word in tokens + joined:
        if word in _WORDS or _squash(word) in _SQUASHED_WORDS:
            return "Let's keep the building friendly. Please rephrase."
    letters = re.sub(r"[^a-z]", "", norm)
    if any(s in letters for s in _SUBSTRINGS):
        return "Let's keep the building friendly. Please rephrase."
    if any(p.search(norm) for p in _PHRASES):
        return "Let's keep the building friendly. Please rephrase."
    return None


def clean(text: str | None, field: str, max_len: int, *, required: bool = False,
          multiline: bool = False) -> str:
    """Normalise whitespace, enforce length and the filter. Raises HTTP 422."""
    text = _CONTROL.sub("", text or "")
    if multiline:
        text = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.replace("\r", "").split("\n"))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
    else:
        text = re.sub(r"\s+", " ", text).strip()
    if required and not text:
        raise HTTPException(422, f"The {field} can't be empty.")
    if len(text) > max_len:
        raise HTTPException(422, f"The {field} can be at most {max_len} characters.")
    reason = problem(text)
    if reason:
        raise HTTPException(422, reason)
    return text
