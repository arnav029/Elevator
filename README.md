# The Internet Elevator

> One building. 10,000 floors. Every floor belongs to a stranger.

The site is one elevator. Press a floor, ride, and the doors open on a small room some stranger built: a 32×32 pixel wall, a message, a few objects. Leave a sticky note, ride somewhere else, or claim an empty floor and build your own.

## Run it locally

You need Python 3.11+ and Node 20+.

```bash
# backend (SQLite and in-memory rate limits by default, seeds itself on first start)
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt     # Windows; use .venv/bin/pip elsewhere
ADMIN_TOKEN=localadmin .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# frontend (dev server with hot reload, proxies /api to :8000)
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Or build the frontend once (`npm run build`) and open http://localhost:8000. FastAPI serves `frontend/dist` and injects Open Graph tags into `/floor/{n}`.

With Docker: `docker compose up --build` runs it on Postgres and Redis at http://localhost:8080.

Tests: `cd backend && .venv/Scripts/python -m pytest`

## What's in it

| Plan item | Where |
|---|---|
| Elevator UI: panel, sliding doors, spinning counter, ding, hum, elevator music | `frontend/src/App.jsx`, `components/Panel.jsx`, `sound.js` (WebAudio, no audio files) |
| Ride time 1.5–4 s by distance; hold the doors or Space to ride faster | `rideTo` / `animate` in `App.jsx` |
| Window by height (street, skyline, clouds, thin sky, stars) and real time of day | `draw.js` `drawWindow` |
| Rooms: 32×32 art, 16 colours, 12 wallpapers, up to 3 objects, 280-char message | `shared/constants.json`, `components/Scene.jsx`, `sprites.js` |
| Claim and edit with a secret edit link (no accounts) | `routes/floors.py`, `components/Editor.jsx`, `KeyModal.jsx` |
| Returning owner sees visits and new notes since last time | `GET /api/floors/{n}/owner`, `InfoCard.jsx` |
| Dice lands only on rooms in the pool | `GET /api/floors/random` |
| Sticky notes (80 chars, newest 30) | `POST /api/floors/{n}/notes` |
| Basement B1–B100: bulb and anonymous text only | `BasementScene`, `rooms.apply_room` |
| Elevator graffiti: last 20 lines on the inside of the doors | `/api/graffiti`, `Doors` in `App.jsx` |
| Breakdowns (1 in 50) onto hand-made half floors | `backend/app/halffloors.py`; add `?breakdown` to the URL to force one |
| Special floors: 0 lobby, 13 missing, 404 brick wall, 10,000 roof | `shared/constants.json` `special` |
| Dust: cobwebs after 30 days, back on the market after 90 | `rooms.dust_sweep`, runs hourly and from the admin page |
| Neighbour hints and stairs | `neighbours` in `GET /api/floors/{n}`, `InfoCard.jsx` |
| Lobby: newest, most visited, floor of the day, floors-claimed counter | `GET /api/lobby`, `LobbyScene` |
| Preview images and per-floor share links | `preview.py` renders a 1200×630 PNG on publish; `main.py` injects OG tags |
| 83 seed rooms ("Furnished by building staff"), 13 basement secrets, 20 graffiti lines | `backend/app/seed.py` |

### Moderation (v1)

- Text filter on every field: profanity, slurs (including spaced-out spellings), links, emails. `backend/app/moderation.py`
- Report button on rooms and notes. 3 distinct reporters auto-hide the item until reviewed.
- New rooms are visitable by link right away. They join the dice pool only after an automated check (named, at least 16 drawn pixels) and a short delay (`DICE_POOL_DELAY_MINUTES`, default 10). `DICE_POOL_MODE=manual` makes every room wait for approval.
- One floor per device, plus IP and device rate limits on claims, edits, notes, graffiti and reports (`ratelimit.py`; Redis when `REDIS_URL` is set).
- Admin page at `/admin` (needs `ADMIN_TOKEN`): review queue, hide, restore, delete, approve for dice, ban author (device and IP), run dust sweep.
- No uploads and no links. IPs and device ids are stored only as HMAC hashes.

## Configuration

| Variable | Default | |
|---|---|---|
| `DATABASE_URL` | `sqlite:///backend/elevator.db` | `postgresql://...` works too |
| `REDIS_URL` | unset | rate limits in memory when unset (fine for one instance) |
| `ADMIN_TOKEN` | unset | admin is disabled without it |
| `SECRET_KEY` | dev value | pepper for hashing IPs and device ids. **Set in production.** |
| `DICE_POOL_MODE` | `auto` | `auto` or `manual` |
| `DICE_POOL_DELAY_MINUTES` | `10` | |
| `RESERVED_TOP_FLOORS` | `0` | e.g. `100` holds back 9,900–9,999 |
| `PUBLIC_URL` | request host | absolute base URL for OG tags |
| `TRUST_PROXY` | `false` | read the client IP from `Fly-Client-IP` / `X-Forwarded-For` |
| `SEED_ON_START` | `true` | furnish the building if the database is empty |

## Deploy (Render, free)

`render.yaml` is a Blueprint: one free Docker web service and one free Postgres database, with `ADMIN_TOKEN` and `SECRET_KEY` generated for you. Open https://render.com/deploy?repo=https://github.com/arnav029/Elevator and apply it. The admin token is under the service's Environment tab.

Free services sleep after 15 minutes idle (the first visit after that takes about a minute). Render's free Postgres expires after 30 days unless upgraded.

## Deploy (Fly.io)

```bash
fly auth login
fly launch --no-deploy --copy-config --name <your-app-name>
fly volumes create elevator_data --size 1
fly secrets set ADMIN_TOKEN=<long random> SECRET_KEY=<long random>
fly deploy
```

This runs on SQLite on a Fly volume, which is fine for a single machine. For more than one machine, attach Postgres (`DATABASE_URL`) and Redis (`REDIS_URL`).

## Not built yet

These are from "Later" and the open decisions in the plan:
- AI lift attendant, live presence, themed weeks
- Optional email to recover a lost edit key
- Moving floors (owners can move out and claim another)

Schema changes use `create_all`; add Alembic once the schema starts to change.
