from datetime import timedelta

from app import art
from app.db import SessionLocal, utcnow
from app.models import Floor
from app.moderation import problem
from app.rooms import dust_sweep
from app.seed import seed

from .conftest import dev

ADMIN = {"X-Admin-Token": "admin-secret"}


def room(name="Test room", **kw):
    return {"name": name, "message": kw.get("message", "hello"),
            "pixels": kw.get("pixels", art.heart().hex()), "wallpaper": kw.get("wallpaper", 2),
            "objects": kw.get("objects", [0, 2])}


def claim(client, n, device=1, **kw):
    return client.post(f"/api/floors/{n}/claim", json=room(**kw), headers=dev(device))


def test_empty_and_special_floors(client):
    r = client.get("/api/floors/500").json()
    assert r["kind"] == "empty" and r["claimable"] and r["window"] == "skyline"
    assert client.get("/api/floors/13").json()["special"] == "missing"
    assert client.get("/api/floors/404").json()["special"] == "brick"
    assert client.get("/api/floors/0").json()["special"] == "lobby"
    assert client.get("/api/floors/10001").status_code == 404
    assert client.get("/api/floors/-5").json()["basement"] is True
    # Neighbours skip the missing 13th floor.
    r = client.get("/api/floors/12").json()
    assert r["neighbours"]["above"]["number"] == 14


def test_claim_edit_and_owner_flow(client):
    r = claim(client, 2417)
    assert r.status_code == 200, r.text
    key = r.json()["owner_key"]
    got = client.get("/api/floors/2417").json()
    assert got["kind"] == "room" and got["room"]["name"] == "Test room"

    assert claim(client, 2417, device=2).status_code == 409  # taken
    assert claim(client, 2418, device=1).status_code == 409  # one floor per device
    assert claim(client, 13, device=3).status_code == 409    # special

    bad = client.put("/api/floors/2417", json=room("New"), headers={**dev(1), "X-Owner-Key": "nope"})
    assert bad.status_code == 403
    ok = client.put("/api/floors/2417", json=room("New name"), headers={**dev(1), "X-Owner-Key": key})
    assert ok.status_code == 200
    assert client.get("/api/floors/2417").json()["room"]["name"] == "New name"

    client.post("/api/floors/2417/notes", json={"body": "nice room"}, headers=dev(5))
    owner = client.get("/api/floors/2417/owner", headers={"X-Owner-Key": key}).json()
    assert owner["new_notes"] == 1 and owner["notes"][0]["new"] is True
    again = client.get("/api/floors/2417/owner", headers={"X-Owner-Key": key}).json()
    assert again["new_notes"] == 0

    png = client.get("/api/floors/2417/preview.png")
    assert png.status_code == 200 and png.content[:4] == b"\x89PNG"

    assert client.delete("/api/floors/2417", headers={"X-Owner-Key": key}).status_code == 200
    assert client.get("/api/floors/2417").json()["kind"] == "empty"


def test_validation_and_filter(client):
    assert claim(client, 5, name="").status_code == 422
    assert claim(client, 5, pixels="z" * 1024).status_code == 422
    assert claim(client, 5, objects=[0, 1, 2, 3]).status_code == 422
    assert claim(client, 5, message="visit www.example.com").status_code == 422
    assert claim(client, 5, name="f.u.c.k this").status_code == 422
    assert problem("Hello from Scunthorpe, Essex") is None
    assert problem("go to example dot com") is not None
    assert problem("n i g g e r") is not None
    # Basement floors keep only anonymous text.
    r = client.post("/api/floors/-4/claim", json={"message": "a secret worth keeping"}, headers=dev(9))
    assert r.status_code == 200
    got = client.get("/api/floors/-4").json()
    assert got["room"]["name"] == "" and got["room"]["message"] == "a secret worth keeping"


def test_visits_are_deduplicated(client):
    claim(client, 7)
    client.get("/api/floors/7?visit=1", headers=dev(2))
    client.get("/api/floors/7?visit=1", headers=dev(2))
    client.get("/api/floors/7?visit=1", headers=dev(3))
    assert client.get("/api/floors/7").json()["room"]["visit_count"] == 2


def test_dice_only_lands_on_pool_floors(client):
    assert client.get("/api/floors/random").status_code == 404
    claim(client, 30, device=1)
    claim(client, 31, device=2, pixels="c" * 1024)  # blank wall fails the automated check
    for _ in range(10):
        assert client.get("/api/floors/random").json()["number"] == 30
    assert client.get("/api/floors/random?exclude=30").status_code == 404


def test_reports_auto_hide_and_admin(client):
    claim(client, 40)
    note = client.post("/api/floors/40/notes", json={"body": "meh"}, headers=dev(2)).json()
    for d in (3, 3, 4):  # duplicate reports from one device count once
        client.post("/api/reports", json={"target_type": "note", "target_id": note["id"]}, headers=dev(d))
    assert len(client.get("/api/floors/40").json()["notes"]) == 1
    client.post("/api/reports", json={"target_type": "note", "target_id": note["id"]}, headers=dev(5))
    assert client.get("/api/floors/40").json()["notes"] == []

    assert client.get("/api/admin/queue").status_code == 401
    q = client.get("/api/admin/queue", headers=ADMIN).json()
    assert any(i["type"] == "note" for i in q["reported"])
    client.post(f"/api/admin/note/{note['id']}/ban", json={"reason": "test"}, headers=ADMIN)
    blocked = client.post("/api/floors/40/notes", json={"body": "again"}, headers=dev(2))
    assert blocked.status_code == 403


def test_rate_limit_on_graffiti(client):
    codes = [client.post("/api/graffiti", json={"body": f"line {i}"}, headers=dev(1)).status_code
             for i in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429
    assert len(client.get("/api/graffiti").json()) == 3


def test_dust_and_reclaim(client):
    claim(client, 60, device=1)
    claim(client, 61, device=2)
    now = utcnow()
    with SessionLocal() as db:
        a, b = db.get(Floor, 60), db.get(Floor, 61)
        a.last_visited_at = now - timedelta(days=31)
        b.last_visited_at = b.owner_seen_at = now - timedelta(days=91)
        db.commit()
        assert dust_sweep(db, now) == {"dusted": 2, "reclaimed": 1}
    assert client.get("/api/floors/60").json()["room"]["dusty"] is True
    assert client.get("/api/floors/61").json()["kind"] == "empty"
    # A visit blows the cobwebs away.
    client.get("/api/floors/60?visit=1", headers=dev(7))
    assert client.get("/api/floors/60").json()["room"]["dusty"] is False


def test_seed_lobby_and_half_floors(client):
    with SessionLocal() as db:
        assert seed(db) > 50
        assert seed(db) == 0
    lobby = client.get("/api/lobby").json()
    assert lobby["claimed"] > 50 and lobby["floor_of_the_day"] and len(lobby["newest"]) == 8
    assert len(client.get("/api/graffiti").json()) == 20
    half = client.get("/api/half-floors/pick?from=1&to=10").json()
    assert half["at"] in (1, 7)


def test_floor_page_has_og_tags(client):
    claim(client, 77, name="Lucky room")
    page = client.get("/floor/77").text
    assert 'og:image' in page and "/api/floors/77/preview.png" in page and "Lucky room" in page
    assert "/api/floors/-3/preview.png" in client.get("/floor/B3").text
