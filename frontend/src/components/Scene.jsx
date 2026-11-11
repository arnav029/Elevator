import { useEffect, useState } from 'react'
import { api } from '../api'
import { OBJECTS, WALLPAPERS, halfLabel, label, windowView } from '../constants'
import { SPRITE_SCALE } from '../sprites'
import { PixelArt, Sprite, WindowView } from './Canvases'

const SLOTS = [
  { left: '6%' },
  { left: '44%' },
  { left: '76%' },
]

function Cobwebs() {
  const web = (
    <svg viewBox="0 0 60 60" className="cobweb">
      <g stroke="rgba(255,255,255,0.75)" strokeWidth="0.8" fill="none">
        <path d="M0 0 L60 8 M0 0 L48 32 M0 0 L30 50 M0 0 L8 60" />
        <path d="M14 2 Q12 8 4 14 M28 4 Q22 16 8 28 M42 6 Q32 26 12 42 M56 8 Q44 34 16 56" />
      </g>
    </svg>
  )
  return (
    <>
      <div className="cobweb-corner tl">{web}</div>
      <div className="cobweb-corner tr">{web}</div>
    </>
  )
}

export function RoomScene({ n, room, notes = [], fresh }) {
  const wall = WALLPAPERS[room.wallpaper]?.color || WALLPAPERS[0].color
  const view = windowView(n)
  const objects = (room.objects || []).map((o) => OBJECTS[o]).filter(Boolean)
  return (
    <div className="scene room" style={{ '--wall': wall }}>
      <div className="wall" />
      <div className="floorboards" />
      {view && <WindowView view={view} floor={n} />}
      <div className="art-frame">
        <PixelArt pixels={room.pixels} />
      </div>
      {room.name && <div className="plaque">{room.name}</div>}
      <div className="wall-notes">
        {notes.slice(0, 6).map((note, i) => (
          <div key={note.id} className="wall-note" style={{ '--r': `${((note.id * 37) % 13) - 6}deg`, '--i': i }} title={note.body}>
            {note.body}
          </div>
        ))}
      </div>
      {objects.map((name, i) => (
        <Sprite
          key={`${name}-${i}`}
          name={name}
          className={name === 'rug' ? 'flat' : ''}
          style={{ ...SLOTS[i], width: `${(SPRITE_SCALE[name] || 1) * 13}%` }}
        />
      ))}
      {room.dusty && <Cobwebs />}
      {room.dusty && fresh && <div className="dust-puff">you brush away the cobwebs</div>}
    </div>
  )
}

export function BasementScene({ n, room }) {
  return (
    <div className="scene basement">
      <div className="pipe p1" />
      <div className="pipe p2" />
      <div className="bulb-cord" />
      <div className="bulb" />
      <div className="bulb-glow" />
      <div className="basement-label">{label(n)}</div>
      {room ? <p className="confession">{room.message}</p> : <p className="confession empty">Nothing down here yet. Just the hum of the boiler.</p>}
    </div>
  )
}

export function EmptyScene({ n, basement, reserved }) {
  if (basement) return <BasementScene n={n} />
  const view = windowView(n)
  return (
    <div className="scene empty">
      {view && <WindowView view={view} floor={n} />}
      <div className="concrete-floor" />
      <div className="rent-sign">
        <div className="rent-title">{reserved ? 'RESERVED' : 'FOR RENT'}</div>
        <div className="rent-sub">{reserved ? 'held by management' : `floor ${label(n)} · inquire within`}</div>
      </div>
      <div className="bucket" />
    </div>
  )
}

export function BrickScene() {
  return (
    <div className="scene brick">
      <div className="chalk">
        404
        <small>floor not found</small>
      </div>
    </div>
  )
}

export function RoofScene() {
  const [stars] = useState(() =>
    Array.from({ length: 90 }, (_, i) => ({ x: (i * 73.7) % 100, y: (i * 41.3) % 78, s: 1 + (i % 3), d: (i % 7) * 0.4 })),
  )
  return (
    <div className="scene roof">
      {stars.map((s, i) => (
        <div key={i} className="star" style={{ left: `${s.x}%`, top: `${s.y}%`, width: s.s, height: s.s, animationDelay: `${s.d}s` }} />
      ))}
      <div className="shooting-star" />
      <div className="railing" />
      <div className="roof-label">THE ROOF · FLOOR 10,000</div>
    </div>
  )
}

export function HiddenScene() {
  return (
    <div className="scene hidden-floor">
      <div className="tape t1">CLOSED FOR INSPECTION</div>
      <div className="tape t2">CLOSED FOR INSPECTION</div>
    </div>
  )
}

export function HalfScene({ half }) {
  return (
    <div className={`scene half half-${half.style}`}>
      <div className="low-ceiling" />
      <div className="art-frame half-art">
        <PixelArt pixels={half.pixels} />
      </div>
      <div className="half-label">{halfLabel(half.at)}</div>
      <div className="half-glow" />
    </div>
  )
}

export function LobbyScene({ onRide }) {
  const [lobby, setLobby] = useState(null)
  useEffect(() => {
    api.lobby().then(setLobby).catch(() => setLobby({ newest: [], most_visited: [], claimed: 0, total: 0 }))
  }, [])
  const item = (f) => (
    <li key={f.number}>
      <button onClick={() => onRide(f.number)}>
        <span className="dir-n">{label(f.number)}</span>
        <span className="dir-name">{f.name}</span>
      </button>
    </li>
  )
  return (
    <div className="scene lobby">
      <div className="lobby-floor" />
      <div className="directory">
        <div className="dir-head">BUILDING DIRECTORY</div>
        {!lobby ? (
          <div className="dir-loading">…</div>
        ) : (
          <>
            {lobby.floor_of_the_day && (
              <div className="dir-otd">
                <span>Floor of the day</span>
                <button onClick={() => onRide(lobby.floor_of_the_day.number)}>
                  {label(lobby.floor_of_the_day.number)} · {lobby.floor_of_the_day.name}
                </button>
              </div>
            )}
            <div className="dir-cols">
              <div>
                <div className="dir-sub">NEW TENANTS</div>
                <ul>{lobby.newest.map(item)}</ul>
              </div>
              <div>
                <div className="dir-sub">MOST VISITED</div>
                <ul>{lobby.most_visited.map(item)}</ul>
              </div>
            </div>
            <div className="dir-claimed">
              {lobby.claimed.toLocaleString()} of {lobby.total.toLocaleString()} floors claimed
            </div>
          </>
        )}
      </div>
    </div>
  )
}

/** Picks the right scene for wherever the elevator currently is. */
export function Scene({ here, onRide, fresh }) {
  if (here.half) return <HalfScene half={here.half} />
  const d = here.data
  if (!d) return <div className="scene loading" />
  if (d.error) return <div className="scene loading"><p className="scene-error">{d.error}</p></div>
  if (d.kind === 'special') {
    if (d.special === 'lobby') return <LobbyScene onRide={onRide} />
    if (d.special === 'brick') return <BrickScene />
    if (d.special === 'roof') return <RoofScene />
  }
  if (d.kind === 'hidden') return <HiddenScene />
  if (d.kind === 'empty') return <EmptyScene n={d.number} basement={d.basement} reserved={d.reserved} />
  if (d.kind === 'room') {
    if (d.basement) return <BasementScene n={d.number} room={d.room} />
    return <RoomScene n={d.number} room={d.room} notes={d.notes} fresh={fresh} />
  }
  return <div className="scene loading" />
}
